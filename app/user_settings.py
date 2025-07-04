from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from threading import Thread

db = SQLAlchemy()

# ===== DATABASE MODELS =====

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=True)  # For SMS notifications
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    preferences = db.relationship('UserPreference', backref='user', uselist=False, cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user', lazy=True, cascade='all, delete-orphan')

class UserPreference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Notification preferences for different report types
    fire_hazard = db.Column(db.Boolean, default=False)
    faulty_equipment = db.Column(db.Boolean, default=False)
    vandalism = db.Column(db.Boolean, default=False)
    suspicious_activity = db.Column(db.Boolean, default=False)
    other_incident = db.Column(db.Boolean, default=False)
    
    # Privacy preferences
    location_access = db.Column(db.Boolean, default=False)
    camera_access = db.Column(db.Boolean, default=False)
    data_sharing = db.Column(db.Boolean, default=False)
    
    # Delivery preferences
    email_notifications = db.Column(db.Boolean, default=True)
    sms_notifications = db.Column(db.Boolean, default=False)
    browser_notifications = db.Column(db.Boolean, default=False)
    
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)  # 'fire_hazard', 'faulty_equipment', etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Add relationship to user
    author = db.relationship('User', backref='reports')

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    report_id = db.Column(db.Integer, db.ForeignKey('report.id'), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    report = db.relationship('Report', backref='notifications')

# ===== FLASK BLUEPRINT =====

settings_bp = Blueprint('settings', __name__)

# ===== EMAIL CONFIGURATION =====

class EmailConfig:
    # Configure these in your environment variables or config file
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    SENDER_EMAIL = os.getenv('SENDER_EMAIL', 'your-app@example.com')
    SENDER_PASSWORD = os.getenv('SENDER_PASSWORD', 'your-app-password')
    APP_NAME = os.getenv('APP_NAME', 'Your App Name')

# ===== ROUTES =====

@settings_bp.route('/settings')
def settings_page():
    """Render the settings page"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        return redirect(url_for('auth.login'))
    
    return render_template('5_settings.html', user=user)

@settings_bp.route('/api/settings', methods=['GET'])
def get_settings():
    """Get current user settings"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_id = session['user_id']
    preferences = UserPreference.query.filter_by(user_id=user_id).first()
    
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
        'fireHazard': preferences.fire_hazard,
        'faultyEquipment': preferences.faulty_equipment,
        'vandalism': preferences.vandalism,
        'suspiciousActivity': preferences.suspicious_activity,
        'otherIncident': preferences.other_incident,
        'locationAccess': preferences.location_access,
        'cameraAccess': preferences.camera_access,
        'dataSharing': preferences.data_sharing,
        'emailNotifications': preferences.email_notifications,
        'smsNotifications': preferences.sms_notifications,
        'browserNotifications': preferences.browser_notifications
    })

@settings_bp.route('/api/settings', methods=['POST'])
def update_settings():
    """Update user settings"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_id = session['user_id']
    data = request.get_json()
    
    # Get or create user preferences
    preferences = UserPreference.query.filter_by(user_id=user_id).first()
    if not preferences:
        preferences = UserPreference(user_id=user_id)
        db.session.add(preferences)
    
    # Update notification preferences
    preferences.fire_hazard = data.get('fireHazard', False)
    preferences.faulty_equipment = data.get('faultyEquipment', False)
    preferences.vandalism = data.get('vandalism', False)
    preferences.suspicious_activity = data.get('suspiciousActivity', False)
    preferences.other_incident = data.get('otherIncident', False)
    
    # Update privacy preferences
    preferences.location_access = data.get('locationAccess', False)
    preferences.camera_access = data.get('cameraAccess', False)
    preferences.data_sharing = data.get('dataSharing', False)
    
    # Update delivery preferences
    preferences.email_notifications = data.get('emailNotifications', True)
    preferences.sms_notifications = data.get('smsNotifications', False)
    preferences.browser_notifications = data.get('browserNotifications', False)
    
    try:
        db.session.commit()
        return jsonify({'message': 'Settings updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error updating settings: {str(e)}")
        return jsonify({'error': 'Failed to update settings'}), 500

# ===== NOTIFICATION SYSTEM =====

def send_notifications_for_new_report(report):
    """Send notifications to users who have enabled notifications for this report category"""
    
    # Map report categories to preference fields
    category_mapping = {
        'fire_hazard': 'fire_hazard',
        'faulty_equipment': 'faulty_equipment',
        'vandalism': 'vandalism',
        'suspicious_activity': 'suspicious_activity',
        'other_incident': 'other_incident'
    }
    
    preference_field = category_mapping.get(report.category)
    if not preference_field:
        print(f"Unknown report category: {report.category}")
        return
    
    # Get users who want notifications for this category
    users_to_notify = db.session.query(User).join(UserPreference).filter(
        getattr(UserPreference, preference_field) == True,
        User.id != report.user_id  # Don't notify the report creator
    ).all()
    
    print(f"Found {len(users_to_notify)} users to notify for {report.category} report")
    
    for user in users_to_notify:
        # Create in-app notification
        notification = Notification(
            user_id=user.id,
            report_id=report.id,
            message=f"New {report.category.replace('_', ' ').title()} report: {report.title}"
        )
        db.session.add(notification)
        
        # Get user's delivery preferences
        preferences = user.preferences
        if preferences:
            # Send email notification if enabled
            if preferences.email_notifications:
                send_email_notification_async(user, report)
            
            # Send SMS notification if enabled (you'll need to implement this)
            if preferences.sms_notifications:
                send_sms_notification_async(user, report)
        
        print(f"Notification queued for user {user.username}")
    
    try:
        db.session.commit()
        print("All notifications saved successfully")
    except Exception as e:
        db.session.rollback()
        print(f"Error saving notifications: {str(e)}")

def send_email_notification_async(user, report):
    """Send email notification in a background thread"""
    thread = Thread(target=send_email_notification, args=(user, report))
    thread.daemon = True
    thread.start()

def send_email_notification(user, report):
    """Send email notification to user"""
    try:
        config = EmailConfig()
        
        msg = MIMEMultipart()
        msg['From'] = config.SENDER_EMAIL
        msg['To'] = user.email
        msg['Subject'] = f"🔔 New {report.category.replace('_', ' ').title()} Report Alert"
        
        # Create HTML email body
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #e74c3c;">📢 New Report Alert</h2>
                
                <p>Hello <strong>{user.username}</strong>,</p>
                
                <p>A new report has been submitted in a category you're subscribed to:</p>
                
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #467b65;">
                    <h3 style="margin-top: 0; color: #467b65;">📋 Report Details</h3>
                    <p><strong>Category:</strong> {report.category.replace('_', ' ').title()}</p>
                    <p><strong>Title:</strong> {report.title}</p>
                    <p><strong>Description:</strong> {report.description[:200]}{'...' if len(report.description) > 200 else ''}</p>
                    <p><strong>Submitted:</strong> {report.created_at.strftime('%B %d, %Y at %I:%M %p')}</p>
                </div>
                
                <p style="margin-top: 30px;">
                    <a href="http://your-domain.com/reports/{report.id}" 
                       style="background-color: #467b65; color: white; padding: 12px 24px; 
                              text-decoration: none; border-radius: 6px; display: inline-block;">
                        View Full Report
                    </a>
                </p>
                
                <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
                
                <p style="font-size: 14px; color: #6c757d;">
                    You're receiving this because you've enabled notifications for {report.category.replace('_', ' ').title()} reports. 
                    You can change your notification preferences in your 
                    <a href="http://your-domain.com/settings" style="color: #467b65;">account settings</a>.
                </p>
                
                <p style="font-size: 12px; color: #999;">
                    Best regards,<br>
                    The {config.APP_NAME} Team
                </p>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_body, 'html'))
        
        server = smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT)
        server.starttls()
        server.login(config.SENDER_EMAIL, config.SENDER_PASSWORD)
        text = msg.as_string()
        server.sendmail(config.SENDER_EMAIL, user.email, text)
        server.quit()
        
        print(f"Email notification sent successfully to {user.email}")
        
    except Exception as e:
        print(f"Failed to send email to {user.email}: {str(e)}")

def send_sms_notification_async(user, report):
    """Send SMS notification in a background thread"""
    thread = Thread(target=send_sms_notification, args=(user, report))
    thread.daemon = True
    thread.start()

def send_sms_notification(user, report):
    """Send SMS notification to user (implement with Twilio or similar service)"""
    try:
        # This is a placeholder - implement with your SMS service
        # Example with Twilio:
        # from twilio.rest import Client
        # client = Client(account_sid, auth_token)
        # message = client.messages.create(
        #     body=f"New {report.category.replace('_', ' ').title()} report: {report.title}",
        #     from_='+1234567890',
        #     to=user.phone
        # )
        print(f"SMS notification would be sent to {user.phone} about {report.title}")
        
    except Exception as e:
        print(f"Failed to send SMS to {user.phone}: {str(e)}")

# ===== INTEGRATION WITH EXISTING REPORT SYSTEM =====

# Add this to your existing report submission route
def integrate_with_report_submission():
    """
    Example of how to integrate with your existing report submission system.
    Add this call to your existing report creation route.
    """
    
    # In your existing report route (e.g., in report_submission.py), add:
    """
    @report_bp.route('/api/reports', methods=['POST'])
    def create_report():
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        data = request.get_json()
        
        # Your existing report creation logic
        report = Report(
            title=data['title'],
            description=data['description'],
            category=data['category'],  # Make sure this matches our category mapping
            user_id=session['user_id']
        )
        
        db.session.add(report)
        db.session.commit()
        
        # NEW: Add notification system call
        from user_settings import send_notifications_for_new_report
        send_notifications_for_new_report(report)
        
        return jsonify({'message': 'Report created successfully', 'report_id': report.id}), 201
    """

# ===== ADDITIONAL API ENDPOINTS =====

@settings_bp.route('/api/notifications/unread', methods=['GET'])
def get_unread_notifications():
    """Get all unread notifications for the current user"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_id = session['user_id']
    notifications = Notification.query.filter_by(
        user_id=user_id, 
        is_read=False
    ).order_by(Notification.created_at.desc()).limit(50).all()
    
    notification_list = []
    for notification in notifications:
        notification_list.append({
            'id': notification.id,
            'message': notification.message,
            'created_at': notification.created_at.isoformat(),
            'report_id': notification.report_id
        })
    
    return jsonify(notification_list)

@settings_bp.route('/api/notifications/<int:notification_id>/mark-read', methods=['POST'])
def mark_notification_read(notification_id):
    """Mark a specific notification as read"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_id = session['user_id']
    notification = Notification.query.filter_by(
        id=notification_id, 
        user_id=user_id
    ).first()
    
    if not notification:
        return jsonify({'error': 'Notification not found'}), 404
    
    notification.is_read = True
    db.session.commit()
    
    return jsonify({'message': 'Notification marked as read'}), 200

# ===== UTILITY FUNCTIONS =====

def create_default_preferences(user_id):
    """Create default preferences for a new user"""
    preferences = UserPreference(
        user_id=user_id,
        email_notifications=True,  # Default to email notifications enabled
        sms_notifications=False,
        browser_notifications=False
    )
    db.session.add(preferences)
    db.session.commit()
    return preferences

def get_notification_summary(user_id):
    """Get a summary of user's notification preferences"""
    preferences = UserPreference.query.filter_by(user_id=user_id).first()
    if not preferences:
        return "No preferences set"
    
    enabled_categories = []
    if preferences.fire_hazard:
        enabled_categories.append("Fire Hazards")
    if preferences.faulty_equipment:
        enabled_categories.append("Faulty Equipment")
    if preferences.vandalism:
        enabled_categories.append("Vandalism")
    if preferences.suspicious_activity:
        enabled_categories.append("Suspicious Activities")
    if preferences.other_incident:
        enabled_categories.append("Other Incidents")
    
    if not enabled_categories:
        return "No notification categories enabled"
    
    return f"Notifications enabled for: {', '.join(enabled_categories)}"

# ===== TESTING FUNCTION =====

@settings_bp.route('/api/test-notification', methods=['POST'])
def test_notification():
    """Test notification system (remove in production)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Create a test report
    test_report = Report(
        title="Test Fire Hazard Report",
        description="This is a test notification to verify the system is working.",
        category="fire_hazard",
        user_id=session['user_id']
    )
    
    db.session.add(test_report)
    db.session.commit()
    
    # Send test notifications
    send_notifications_for_new_report(test_report)
    
    return jsonify({'message': 'Test notification sent'}), 200