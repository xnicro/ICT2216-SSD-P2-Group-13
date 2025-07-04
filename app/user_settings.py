from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for, flash, current_app
import mysql.connector
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from threading import Thread

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
                'locationAccess': False,
                'cameraAccess': False,
                'dataSharing': False,
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
            'locationAccess': bool(preferences['location_access']),
            'cameraAccess': bool(preferences['camera_access']),
            'dataSharing': bool(preferences['data_sharing']),
            'emailNotifications': bool(preferences['email_notifications']),
            'smsNotifications': bool(preferences['sms_notifications']),
            'browserNotifications': bool(preferences['browser_notifications'])
        })
        
    except Exception as e:
        print(f"Error getting settings: {str(e)}", flush=True)
        return jsonify({'error': 'Failed to get settings'}), 500

@settings_bp.route('/api/settings', methods=['POST'])
def update_settings():
    """Update user settings"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
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
            cursor.execute('''
                UPDATE user_preferences SET
                    fire_hazard = %s,
                    faulty_equipment = %s,
                    vandalism = %s,
                    suspicious_activity = %s,
                    other_incident = %s,
                    location_access = %s,
                    camera_access = %s,
                    data_sharing = %s,
                    email_notifications = %s,
                    sms_notifications = %s,
                    browser_notifications = %s,
                    updated_at = NOW()
                WHERE user_id = %s
            ''', (
                data.get('fireHazard', False),
                data.get('faultyEquipment', False),
                data.get('vandalism', False),
                data.get('suspiciousActivity', False),
                data.get('otherIncident', False),
                data.get('locationAccess', False),
                data.get('cameraAccess', False),
                data.get('dataSharing', False),
                data.get('emailNotifications', True),
                data.get('smsNotifications', False),
                data.get('browserNotifications', False),
                user_id
            ))
        else:
            # Insert new preferences
            cursor.execute('''
                INSERT INTO user_preferences (
                    user_id, fire_hazard, faulty_equipment, vandalism,
                    suspicious_activity, other_incident, location_access,
                    camera_access, data_sharing, email_notifications,
                    sms_notifications, browser_notifications, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            ''', (
                user_id,
                data.get('fireHazard', False),
                data.get('faultyEquipment', False),
                data.get('vandalism', False),
                data.get('suspiciousActivity', False),
                data.get('otherIncident', False),
                data.get('locationAccess', False),
                data.get('cameraAccess', False),
                data.get('dataSharing', False),
                data.get('emailNotifications', True),
                data.get('smsNotifications', False),
                data.get('browserNotifications', False)
            ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'Settings updated successfully'}), 200
        
    except Exception as e:
        print(f"Error updating settings: {str(e)}", flush=True)
        return jsonify({'error': 'Failed to update settings'}), 500

# ===== NOTIFICATION SYSTEM =====

# Modified send_notifications_for_new_report function
def send_notifications_for_new_report(report_id, report_title, report_description, report_category_name, report_user_id):
    """Send notifications to users who have enabled notifications for this report category"""
    
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
        print(f"Unknown report category: {report_category_name}")
        return
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get users who want notifications for this category
        query = f'''
            SELECT u.user_id, u.username, u.email, up.*
            FROM users u
            JOIN user_preferences up ON u.user_id = up.user_id
            WHERE up.{preference_field} = 1 
            AND u.user_id != %s
        '''
        
        cursor.execute(query, (report_user_id,))
        users_to_notify = cursor.fetchall()
        
        print(f"Found {len(users_to_notify)} users to notify for {report_category_name} report")
        
        for user in users_to_notify:
            # Create in-app notification
            cursor.execute('''
                INSERT INTO notification (user_id, report_id, message, is_read, created_at)
                VALUES (%s, %s, %s, 0, NOW())
            ''', (
                user['user_id'],
                report_id,
                f"New {report_category_name} report: {report_title}"
            ))
            
            # Send email notification if enabled
            if user['email_notifications']:
                send_email_notification_async(
                    user['email'], 
                    user['username'],
                    report_id,
                    report_title,
                    report_description,
                    report_category_name  # Pass display name directly
                )
            
            print(f"Notification queued for user {user['username']}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("All notifications saved successfully")
        
    except Exception as e:
        print(f"Error sending notifications: {str(e)}")

def send_email_notification_async(email, username, report_id, report_title, report_description, report_category):
    """Send email notification in a background thread"""
    thread = Thread(target=send_email_notification, args=(email, username, report_id, report_title, report_description, report_category))
    thread.daemon = True
    thread.start()

def send_email_notification(email, username, report_id, report_title, report_description, report_category):
    """Send email notification to user"""
    try:
        # Email configuration
        SMTP_SERVER = current_app.config.get('SMTP_SERVER', 'smtp.gmail.com')
        SMTP_PORT = current_app.config.get('SMTP_PORT', 587)
        SENDER_EMAIL = current_app.config.get('SENDER_EMAIL', 'your-app@example.com')
        SENDER_PASSWORD = current_app.config.get('SENDER_PASSWORD', 'your-app-password')
        APP_NAME = current_app.config.get('APP_NAME', 'Your App Name')
        
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = email
        msg['Subject'] = f"🔔 New {report_category.replace('_', ' ').title()} Report Alert"
        
        # Create HTML email body
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #e74c3c;">📢 New Report Alert</h2>
                
                <p>Hello <strong>{username}</strong>,</p>
                
                <p>A new report has been submitted in a category you're subscribed to:</p>
                
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #467b65;">
                    <h3 style="margin-top: 0; color: #467b65;">📋 Report Details</h3>
                    <p><strong>Category:</strong> {report_category.replace('_', ' ').title()}</p>
                    <p><strong>Title:</strong> {report_title}</p>
                    <p><strong>Description:</strong> {report_description[:200]}{'...' if len(report_description) > 200 else ''}</p>
                    <p><strong>Submitted:</strong> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
                </div>
                
                <p style="margin-top: 30px;">
                    <a href="http://localhost:5000/report/{report_id}" 
                       style="background-color: #467b65; color: white; padding: 12px 24px; 
                              text-decoration: none; border-radius: 6px; display: inline-block;">
                        View Full Report
                    </a>
                </p>
                
                <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
                
                <p style="font-size: 14px; color: #6c757d;">
                    You're receiving this because you've enabled notifications for {report_category.replace('_', ' ').title()} reports. 
                    You can change your notification preferences in your 
                    <a href="http://localhost:5000/settings" style="color: #467b65;">account settings</a>.
                </p>
                
                <p style="font-size: 12px; color: #999;">
                    Best regards,<br>
                    The {APP_NAME} Team
                </p>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_body, 'html'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        text = msg.as_string()
        server.sendmail(SENDER_EMAIL, email, text)
        server.quit()
        
        print(f"Email notification sent successfully to {email}")
        
    except Exception as e:
        print(f"Failed to send email to {email}: {str(e)}")

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

# ===== TESTING FUNCTION =====

@settings_bp.route('/api/test-notification', methods=['POST'])
def test_notification():
    """Test notification system"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        # Create a test report
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO reports (title, description, category, user_id, status_id, created_at)
            VALUES (%s, %s, %s, %s, 1, NOW())
        ''', (
            "Test Fire Hazard Report",
            "This is a test notification to verify the system is working.",
            "fire_hazard",
            session['user_id']
        ))
        
        report_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        
        # Send test notifications
        send_notifications_for_new_report(
            report_id,
            "Test Fire Hazard Report",
            "This is a test notification to verify the system is working.",
            "fire_hazard",
            session['user_id']
        )
        
        return jsonify({'message': 'Test notification sent'}), 200
        
    except Exception as e:
        print(f"Error sending test notification: {str(e)}")
        return jsonify({'error': 'Failed to send test notification'}), 500