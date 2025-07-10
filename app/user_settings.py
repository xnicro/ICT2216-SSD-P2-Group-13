from flask import Blueprint, request, jsonify, session, current_app
import mysql.connector
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from threading import Thread
from access_control import permission_required
from flask_wtf.csrf import validate_csrf
from wtforms.validators import ValidationError
from extensions import limiter

settings_bp = Blueprint('settings', __name__)

# ===== DATABASE HELPER FUNCTIONS =====

def get_db_connection():
    """Get MySQL database connection using app config"""
    return mysql.connector.connect(
        host=current_app.config['MYSQL_HOST'],
        user=current_app.config['MYSQL_USER'],
        password=current_app.config['MYSQL_PASSWORD'],
        database=current_app.config['MYSQL_DB']
    )

# ===== ROUTES =====

@settings_bp.route('/api/settings', methods=['GET'])
def get_settings():
    """Get current user settings"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_id = session['user_id']
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get user preferences
        cursor.execute('''
            SELECT * FROM user_preferences WHERE user_id = %s
        ''', (user_id,))
        
        preferences = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not preferences:
            # Return default preferences
            return jsonify({
                'fireHazard': False,
                'faultyEquipment': False,
                'vandalism': False,
                'suspiciousActivity': False,
                'otherIncident': False,
                'emailNotifications': True,
                'smsNotifications': False,
                'browserNotifications': False
            })
        
        return jsonify({
            'fireHazard': bool(preferences['fire_hazard']),
            'faultyEquipment': bool(preferences['faulty_equipment']),
            'vandalism': bool(preferences['vandalism']),
            'suspiciousActivity': bool(preferences['suspicious_activity']),
            'otherIncident': bool(preferences['other_incident']),
            'emailNotifications': bool(preferences['email_notifications']),
            'smsNotifications': bool(preferences['sms_notifications']),
            'browserNotifications': bool(preferences['browser_notifications'])
        })
        
    except Exception as e:
        print(f"Error getting settings: {str(e)}", flush=True)
        return jsonify({'error': 'Failed to get settings'}), 500

@settings_bp.route('/api/settings', methods=['POST'])
@limiter.limit("5 per minute")
@permission_required('update_user_settings')
def update_settings():
    """Update user settings"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Validate CSRF token
    csrf_token = request.headers.get('X-CSRF-Token')
    try:
        validate_csrf(csrf_token)
    except ValidationError:
        return jsonify({'error': 'Invalid or missing CSRF token'}), 400
    
    user_id = session['user_id']
    data = request.get_json()
    
    print(f"Updating settings for user_id: {user_id}", flush=True)
    print(f"Received data: {data}", flush=True)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Check if preferences exist
        cursor.execute('SELECT id FROM user_preferences WHERE user_id = %s', (user_id,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing preferences
            # Convert boolean to int for tinyint(1) fields
            cursor.execute('''
                UPDATE user_preferences SET
                    fire_hazard = %s,
                    faulty_equipment = %s,
                    vandalism = %s,
                    suspicious_activity = %s,
                    other_incident = %s,
                    email_notifications = %s,
                    sms_notifications = %s,
                    browser_notifications = %s,
                    updated_at = NOW()
                WHERE user_id = %s
            ''', (
                int(data.get('fireHazard', False)),
                int(data.get('faultyEquipment', False)),
                int(data.get('vandalism', False)),
                int(data.get('suspiciousActivity', False)),
                int(data.get('otherIncident', False)),
                int(data.get('emailNotifications', True)),
                int(data.get('smsNotifications', False)),
                int(data.get('browserNotifications', False)),
                user_id
            ))
        else:
            # Insert new preferences
            cursor.execute('''
                INSERT INTO user_preferences (
                    user_id, fire_hazard, faulty_equipment, vandalism,
                    suspicious_activity, other_incident, email_notifications,
                    sms_notifications, browser_notifications, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            ''', (
                user_id,
                int(data.get('fireHazard', False)),
                int(data.get('faultyEquipment', False)),
                int(data.get('vandalism', False)),
                int(data.get('suspiciousActivity', False)),
                int(data.get('otherIncident', False)),
                int(data.get('emailNotifications', True)),
                int(data.get('smsNotifications', False)),
                int(data.get('browserNotifications', False))
            ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Settings updated successfully'}), 200
        
    except Exception as e:
        print(f"Error updating settings: {str(e)}", flush=True)
        return jsonify({'error': 'Failed to update settings'}), 500

# ===== NOTIFICATION SYSTEM =====

def send_notifications_for_new_report(report_id, report_title, report_description, report_category_name, report_user_id):
    """Send notifications to users who have enabled notifications for this report category"""
    current_app.logger.info(f"\n=== STARTING NOTIFICATION PROCESS ===")
    current_app.logger.info(f"Report ID: {report_id}, Category: {report_category_name}, Submitted by: {report_user_id}")
    
    # Map display names to preference field names
    category_mapping = {
        'Fires': 'fire_hazard',
        'Faulty Facilities/Equipment': 'faulty_equipment',
        'Vandalism': 'vandalism',
        'Suspicious Activity': 'suspicious_activity',
        'Others': 'other_incident'
    }
    
    preference_field = category_mapping.get(report_category_name)
    if not preference_field:
        current_app.logger.error(f"Unknown report category: {report_category_name}")
        current_app.logger.info("Available categories: %s", list(category_mapping.keys()))
        return
    
    current_app.logger.info(f"Using preference field: {preference_field}")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get users who want notifications for this category AND have email notifications enabled
        query = f'''
            SELECT u.user_id, u.username, u.email, up.*
            FROM users u
            JOIN user_preferences up ON u.user_id = up.user_id
            WHERE up.{preference_field} = 1 
            AND up.email_notifications = 1
            AND u.user_id != %s
        '''
        
        current_app.logger.info("Executing query:\n%s\nWith params: %s", query, (report_user_id,))
        cursor.execute(query, (report_user_id,))
        users_to_notify = cursor.fetchall()
        
        current_app.logger.info(f"Found {len(users_to_notify)} users to notify")
        
        if not users_to_notify:
            current_app.logger.info("No users found with notifications enabled for this category")
            return
            
        for user in users_to_notify:
            current_app.logger.info(f"Processing user {user['user_id']} ({user['email']})")
            
            # Create in-app notification
            try:
                cursor.execute('''
                    INSERT INTO notification (user_id, report_id, message, is_read, created_at)
                    VALUES (%s, %s, %s, 0, NOW())
                ''', (
                    user['user_id'],
                    report_id,
                    f"New {report_category_name} report: {report_title}"
                ))
                current_app.logger.info("Created in-app notification")
            except Exception as e:
                current_app.logger.error(f"Failed to create in-app notification: {str(e)}")
                continue
                
            # Send email notification
            if user['email_notifications'] and user['email']:
                current_app.logger.info(f"Preparing email to {user['email']}")
                try:
                    app = current_app._get_current_object()
                    thread = Thread(
                        target=send_email_notification_with_context,
                        args=(app, user['email'], user['username'], report_id, report_title, report_description, report_category_name)
                    )
                    thread.daemon = True
                    thread.start()
                    current_app.logger.info("Email thread started successfully")
                except Exception as e:
                    current_app.logger.error(f"Failed to start email thread: {str(e)}")
            else:
                current_app.logger.info("Email notifications disabled or no email address for user")
        
        conn.commit()
        current_app.logger.info("Database changes committed")
        
    except Exception as e:
        current_app.logger.error(f"Error in notification process: {str(e)}")
    finally:
        try:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals() and conn.is_connected():
                conn.close()
        except Exception as e:
            current_app.logger.error(f"Error closing DB connection: {str(e)}")
        
    current_app.logger.info("=== NOTIFICATION PROCESS COMPLETE ===\n")

def send_email_notification_with_context(app, email, username, report_id, report_title, report_description, report_category):
    """Send email notification with app context"""
    with app.app_context():
        send_email_notification(email, username, report_id, report_title, report_description, report_category)

def send_email_notification(email, username, report_id, report_title, report_description, report_category):
    """Send email notification to user"""
    current_app.logger.info(f"\n=== STARTING EMAIL PROCESS ===")
    current_app.logger.info(f"Preparing email to: {email}")
    
    try:
        SMTP_SERVER = current_app.config.get('SMTP_SERVER', 'smtp.gmail.com')
        SMTP_PORT = current_app.config.get('SMTP_PORT', 587)
        SENDER_EMAIL = current_app.config.get('SENDER_EMAIL', 'sitsecure.notifications@gmail.com')
        SENDER_PASSWORD = current_app.config.get('SENDER_PASSWORD', 'your-app-password')
        APP_NAME = current_app.config.get('APP_NAME', 'SITSecure')
        
        current_app.logger.info(f"SMTP Server: {SMTP_SERVER}:{SMTP_PORT}")
        current_app.logger.info(f"Sender: {SENDER_EMAIL}")
        current_app.logger.info(f"Password configured: {'Yes' if SENDER_PASSWORD else 'No'}")
        
        msg = MIMEMultipart()
        msg['From'] = f"{APP_NAME} <{SENDER_EMAIL}>"
        msg['To'] = email
        msg['Subject'] = f"🔔 New {report_category} Report Alert"

        # Create HTML version
        html = f"""
        <html>
        <body>
            <p>Hi {username},</p>
            <p>A new <strong>{report_category}</strong> report has been submitted:</p>
            <h3>{report_title}</h3>
            <p>{report_description}</p>
            <p>
                <a href="{current_app.config.get('BASE_URL', 'https://wesitsecure.zapto.org/login')}">
                    View Report
                </a>
            </p>
        </body>
        </html>
        """

        # Attach both versions
        msg.attach(MIMEText(html, 'html'))

        # Send email
        try:
            with smtplib.SMTP(current_app.config.get('SMTP_SERVER'), 
                            current_app.config.get('SMTP_PORT')) as server:
                server.starttls()
                server.login(current_app.config.get('SENDER_EMAIL'), 
                            current_app.config.get('SENDER_PASSWORD'))
                server.send_message(msg)
            current_app.logger.info(f"Email sent to {email}")
        except Exception as e:
            current_app.logger.error(f"Email failed to {email}: {str(e)}")
            raise  # Re-raise if you want calling code to handle the failure
        
    except smtplib.SMTPAuthenticationError as e:
        current_app.logger.error(f"SMTP Authentication failed: {str(e)}")
        current_app.logger.error("Please verify:")
        current_app.logger.error("1. SENDER_EMAIL is correct")
        current_app.logger.error("2. SENDER_PASSWORD is an App Password (not regular password)")
        current_app.logger.error("3. Less secure apps access is enabled if required")
    except smtplib.SMTPException as e:
        current_app.logger.error(f"SMTP Protocol error: {str(e)}")
    except Exception as e:
        current_app.logger.error(f"Unexpected error sending email: {str(e)}")
    finally:
        current_app.logger.info("=== EMAIL PROCESS COMPLETE ===\n")

# ===== ADDITIONAL API ENDPOINTS =====

@settings_bp.route('/api/notifications/unread', methods=['GET'])
def get_unread_notifications():
    """Get all unread notifications for the current user"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_id = session['user_id']
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('''
            SELECT n.*, r.title as report_title
            FROM notification n
            LEFT JOIN reports r ON n.report_id = r.report_id
            WHERE n.user_id = %s AND n.is_read = 0
            ORDER BY n.created_at DESC
            LIMIT 50
        ''', (user_id,))
        
        notifications = cursor.fetchall()
        cursor.close()
        conn.close()
        
        notification_list = []
        for notification in notifications:
            notification_list.append({
                'id': notification['id'],
                'message': notification['message'],
                'created_at': notification['created_at'].isoformat() if notification['created_at'] else None,
                'report_id': notification['report_id']
            })
        
        return jsonify(notification_list)
        
    except Exception as e:
        print(f"Error getting notifications: {str(e)}")
        return jsonify({'error': 'Failed to get notifications'}), 500

@settings_bp.route('/api/notifications/<int:notification_id>/mark-read', methods=['POST'])
def mark_notification_read(notification_id):
    """Mark a specific notification as read"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_id = session['user_id']
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE notification 
            SET is_read = 1 
            WHERE id = %s AND user_id = %s
        ''', (notification_id, user_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'Notification marked as read'}), 200
        
    except Exception as e:
        print(f"Error marking notification as read: {str(e)}")
        return jsonify({'error': 'Failed to mark notification as read'}), 500