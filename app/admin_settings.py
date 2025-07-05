from flask import Blueprint, request, jsonify, session, current_app
import mysql.connector
from datetime import datetime
from functools import wraps
from access_control import permission_required

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
                'browserNotifications': False,
                'loginAlerts': True,
            })
        
        return jsonify({
            'emailNotifications': bool(preferences['email_notifications']),
            'browserNotifications': bool(preferences['browser_notifications']),
            'loginAlerts': bool(preferences['login_alerts']),
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting admin settings: {str(e)}")
        return jsonify({'error': 'Failed to get admin settings'}), 500

@admin_settings_bp.route('/settings', methods=['POST'])
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
                    login_alerts = %s,
                    session_timeout = %s,
                    updated_at = NOW()
                WHERE user_id = %s
            ''', (
                data.get('emailNotifications', True),
                data.get('browserNotifications', False),
                data.get('loginAlerts', True),
                user_id
            ))
        else:
            # Insert new preferences
            cursor.execute('''
                INSERT INTO admin_preferences (
                    user_id, email_notifications,
                    browser_notifications, login_alerts, session_timeout,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
            ''', (
                user_id,
                data.get('emailNotifications', True),
                data.get('browserNotifications', False),
                data.get('loginAlerts', True)
            ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'Admin settings updated successfully'}), 200
        
    except Exception as e:
        current_app.logger.error(f"Error updating admin settings: {str(e)}")
        return jsonify({'error': 'Failed to update admin settings'}), 500