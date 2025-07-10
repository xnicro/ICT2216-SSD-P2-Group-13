from flask import Blueprint, request, jsonify, session, current_app
import mysql.connector
from functools import wraps
from access_control import permission_required
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from threading import Thread
from extensions import limiter

admin_settings_bp = Blueprint('admin_settings', __name__, url_prefix='/api/admin')

# ===== HELPER FUNCTIONS =====

def admin_required(f):
    """Decorator to ensure user is an admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

def get_db_connection():
    """Get MySQL database connection using app config"""
    return mysql.connector.connect(
        host=current_app.config['MYSQL_HOST'],
        user=current_app.config['MYSQL_USER'],
        password=current_app.config['MYSQL_PASSWORD'],
        database=current_app.config['MYSQL_DB']
    )

# ===== ADMIN SETTINGS ROUTES =====

@admin_settings_bp.route('/settings', methods=['GET'])
@admin_required
def get_admin_settings():
    """Get admin-specific settings"""
    user_id = session['user_id']
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get admin preferences
        cursor.execute('''
            SELECT * FROM admin_preferences WHERE user_id = %s
        ''', (user_id,))
        
        preferences = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not preferences:
            # Return default preferences
            return jsonify({
                'emailNotifications': True,
                'browserNotifications': False
            })
        
        return jsonify({
            'emailNotifications': bool(preferences['email_notifications']),
            'browserNotifications': bool(preferences['browser_notifications'])
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting admin settings: {str(e)}")
        return jsonify({'error': 'Failed to get admin settings'}), 500

@admin_settings_bp.route('/settings', methods=['POST'])
@limiter.limit("5 per minute")
@admin_required
@permission_required('update_admin_settings')
def update_admin_settings():
    """Update admin settings"""
    user_id = session['user_id']
    data = request.get_json()
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Check if preferences exist
        cursor.execute('SELECT id FROM admin_preferences WHERE user_id = %s', (user_id,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing preferences
            cursor.execute('''
                UPDATE admin_preferences SET
                    email_notifications = %s,
                    browser_notifications = %s,
                    updated_at = NOW()
                WHERE user_id = %s
            ''', (
                data.get('emailNotifications', True),
                data.get('browserNotifications', False),
                user_id
            ))
        else:
            # Insert new preferences
            cursor.execute('''
                INSERT INTO admin_preferences (
                    user_id, email_notifications,
                    browser_notifications,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, NOW(), NOW())
            ''', (
                user_id,
                data.get('emailNotifications', True),
                data.get('browserNotifications', False)
            ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'Admin settings updated successfully'}), 200
        
    except Exception as e:
        current_app.logger.error(f"Error updating admin settings: {str(e)}")
        return jsonify({'error': 'Failed to update admin settings'}), 500
    
# ===== NOTIFICATION SYSTEM =====

def send_admin_notifications_for_new_report(report_id, report_title, report_description, report_category_name, report_user_id):
    """Send notifications to admins for all reports"""
    current_app.logger.info(f"\n=== STARTING ADMIN NOTIFICATION PROCESS ===")
    current_app.logger.info(f"Report ID: {report_id}, Category: {report_category_name}, Submitted by: {report_user_id}")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get admins who want notifications AND have email notifications enabled
        query = '''
            SELECT u.user_id, u.username, u.email, up.*
            FROM users u
            JOIN admin_preferences up ON u.user_id = up.user_id
            WHERE u.role = 'admin'
            AND up.email_notifications = 1
            AND u.user_id != %s
        '''
        
        current_app.logger.info("Executing query:\n%s\nWith params: %s", query, (report_user_id,))
        cursor.execute(query, (report_user_id,))
        admins_to_notify = cursor.fetchall()
        
        current_app.logger.info(f"Found {len(admins_to_notify)} admins to notify")
        
        if not admins_to_notify:
            current_app.logger.info("No admins found with notifications enabled")
            return
            
        for admin in admins_to_notify:
            current_app.logger.info(f"Processing admin {admin['user_id']} ({admin['email']})")
            
            # Create in-app notification
            try:
                cursor.execute('''
                    INSERT INTO notification (user_id, report_id, message, is_read, created_at)
                    VALUES (%s, %s, %s, 0, NOW())
                ''', (
                    admin['user_id'],
                    report_id,
                    f"New {report_category_name} report: {report_title}"
                ))
                current_app.logger.info("Created in-app notification for admin")
            except Exception as e:
                current_app.logger.error(f"Failed to create in-app notification for admin: {str(e)}")
                continue
                
            # Send email notification
            if admin['email_notifications'] and admin['email']:
                current_app.logger.info(f"Preparing email to {admin['email']}")
                try:
                    app = current_app._get_current_object()
                    thread = Thread(
                        target=send_email_notification_with_context,
                        args=(app, admin['email'], admin['username'], report_id, report_title, report_description, report_category_name)
                    )
                    thread.daemon = True
                    thread.start()
                    current_app.logger.info("Email thread started successfully for admin")
                except Exception as e:
                    current_app.logger.error(f"Failed to start email thread for admin: {str(e)}")
            else:
                current_app.logger.info("Email notifications disabled or no email address for admin")
        
        conn.commit()
        current_app.logger.info("Database changes committed for admin notifications")
        
    except Exception as e:
        current_app.logger.error(f"Error in admin notification process: {str(e)}")
    finally:
        try:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals() and conn.is_connected():
                conn.close()
        except Exception as e:
            current_app.logger.error(f"Error closing DB connection in admin notifications: {str(e)}")
        
    current_app.logger.info("=== ADMIN NOTIFICATION PROCESS COMPLETE ===\n")

def send_email_notification_with_context(app, email, username, report_id, report_title, report_description, report_category):
    """Send email notification with app context"""
    with app.app_context():
        send_email_notification(email, username, report_id, report_title, report_description, report_category)

def send_email_notification(email, username, report_id, report_title, report_description, report_category):
    """Send email notification to admin"""
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
                <a href="{current_app.config.get('BASE_URL', 'https://yourdomain.com')}/reports/{report_id}">
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