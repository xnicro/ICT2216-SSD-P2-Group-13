from flask import Flask, abort, render_template, redirect, url_for, send_from_directory, session, flash, request, jsonify
from datetime import datetime
from datetime import timedelta
import mysql.connector
import os
from report_submission import bp as reports_bp
from home_dashboard import get_report_by_id, get_report_attachments
from admin_dashboard import get_statuses, get_all_reports
from admin_dashboard import bp as admin_bp
from accounts import bp as accounts_bp
from accounts import get_all_users
from werkzeug.utils import secure_filename
from functools import wraps
from flask_wtf.csrf import CSRFProtect, generate_csrf

app = Flask(__name__)
csrf = CSRFProtect()
csrf.init_app(app)

# SECRET_KEY (for flash messages & sessions)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_secret_key')
csrf = CSRFProtect(app)

# Secure session configuration
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,             # Prevent JS access to session cookie
    SESSION_COOKIE_SECURE=not app.debug,      # Only allow over HTTPS in production
    SESSION_COOKIE_SAMESITE='Lax',            # Helps mitigate CSRF (can use 'Strict' if no third-party use)
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=30)  # Session timeout duration
)

# Initial Configs =================================================
# MySQL configurations
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST', 'mysql')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER', 'x')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD', 'x')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB', 'flask_db')
print("aaa", flush=True)
print(app.config['MYSQL_HOST'],app.config['MYSQL_USER'],app.config['MYSQL_PASSWORD'],app.config['MYSQL_DB'], flush=True)

# Email configuration for notifications
app.config['SMTP_SERVER'] = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
app.config['SMTP_PORT'] = int(os.getenv('SMTP_PORT', 587))
app.config['SENDER_EMAIL'] = os.getenv('SENDER_EMAIL', 'your-app@example.com')
app.config['SENDER_PASSWORD'] = os.getenv('SENDER_PASSWORD', 'your-app-password')
app.config['APP_NAME'] = os.getenv('APP_NAME', 'Your App Name')

# Register blueprints
app.register_blueprint(reports_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(accounts_bp)

# Import and register notification system blueprint
try:
    from user_settings import settings_bp
    app.register_blueprint(settings_bp)
    print("Settings blueprint registered successfully", flush=True)
except ImportError as e:
    print(f"Warning: Could not import settings blueprint: {e}", flush=True)

@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=generate_csrf())

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

def get_db_connection():
    conn = mysql.connector.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DB']
    )
    return conn

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('catch_all', filename='1_login.html'))
        return f(*args, **kwargs)
    return decorated_function

# Helper function to get user by ID
def get_user_by_id(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE user_id = %s', (user_id,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        return user
    except Exception as e:
        print(f"Error getting user: {e}")
        return None

# Helper function to get user reports
def get_user_reports(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # First, let's try a simple query without joining the statuses table
        cursor.execute('''
            SELECT r.*, s.name AS status_name
            FROM reports r
            JOIN status s ON r.status_id = s.status_id
            WHERE r.user_id = %s
            ORDER BY r.created_at DESC
        ''', (user_id,))
        
        reports = cursor.fetchall()
        cursor.close()
        conn.close()
        
        print(f"Found {len(reports)} reports for user_id {user_id}")  # Debug line
        return reports
    except Exception as e:
        print(f"Error getting user reports: {e}")
        return []
    
# Helper function to get user notification count
def get_unread_notification_count(user_id):
    """Get count of unread notifications for a user"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM notification WHERE user_id = %s AND is_read = FALSE', (user_id,))
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return count
    except Exception as e:
        print(f"Error getting notification count: {e}")
        return 0

# Context processor to inject notification count
@app.context_processor
def inject_notification_count():
    """Inject unread notification count into all templates"""
    if 'user_id' in session:
        notification_count = get_unread_notification_count(session['user_id'])
        return dict(notification_count=notification_count)
    return dict(notification_count=0)

# App routes ============================================================
@app.route('/')
def index():
    reports = get_all_reports()
    return render_template('0_index.html', reports=reports)

@app.route('/report/<int:report_id>')
def view_report(report_id):
    report = get_report_by_id(report_id)
    if not report:
        return "Report not found", 404
    return render_template('0_report_detail.html', report=report)

@app.route('/admin')
def admin():
    statuses = get_statuses()
    reports = get_all_reports()
    return render_template('7_admin_dashboard.html', statuses=statuses, reports=reports)

@app.route('/profile')
@login_required
def profile():
    # User profile page with real user data and reports
    user_id = session.get('user_id')
    
    # Get current user data
    current_user = get_user_by_id(user_id)
    if not current_user:
        flash('User not found', 'error')
        return redirect(url_for('catch_all', filename='1_login.html'))
    
    # Get user's reports
    user_reports = get_user_reports(user_id)
    
    return render_template('5_profile.html', 
                         current_user=current_user,
                         user_reports=user_reports)

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    # Update user profile information
    user_id = session.get('user_id')
    
    try:
        # Get form data
        username = request.form.get('username')
        email = request.form.get('email')
        
        # Update user in database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users 
            SET username = %s, email = %s 
            WHERE user_id = %s
        ''', (username, email, user_id))
        conn.commit()
        cursor.close()
        conn.close()
        
        # Update session data
        session['username'] = username
        session['email'] = email
        
        flash('Profile updated successfully!', 'success')
        
    except Exception as e:
        flash(f'Error updating profile: {str(e)}', 'error')
    
    return redirect(url_for('profile'))

@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    # Change user password
    user_id = session.get('user_id')
    
    try:
        # Get form data
        current_password = request.form.get('currentPassword')
        new_password = request.form.get('newPassword')
        confirm_password = request.form.get('confirmPassword')
        
        # Validation
        if not current_password or not new_password or not confirm_password:
            flash('All password fields are required', 'error')
            return redirect(url_for('profile'))
        
        if new_password != confirm_password:
            flash('New passwords do not match', 'error')
            return redirect(url_for('profile'))
        
        # Get current user data
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE user_id = %s', (user_id,))
        user = cursor.fetchone()
        
        if not user:
            flash('User not found', 'error')
            return redirect(url_for('profile'))
        
        # Import password hasher
        from accounts import ph
        from argon2.exceptions import VerifyMismatchError
        
        # Verify current password
        try:
            ph.verify(user['pwd'], current_password)
        except VerifyMismatchError:
            flash('Current password is incorrect', 'error')
            cursor.close()
            conn.close()
            return redirect(url_for('profile'))
        
        # Hash new password and update
        new_hashed_password = ph.hash(new_password)
        cursor.execute('''
            UPDATE users 
            SET pwd = %s 
            WHERE user_id = %s
        ''', (new_hashed_password, user_id))
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Password changed successfully!', 'success')
        
    except Exception as e:
        flash(f'Error changing password: {str(e)}', 'error')
    
    return redirect(url_for('profile'))

@app.route('/api/report/<int:report_id>')
@login_required
def get_report_details(report_id):
    # Get report details for the modal
    user_id = session.get('user_id')
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get report details - ensure user owns this report
        cursor.execute('''
            SELECT r.*, 
                   CASE 
                       WHEN r.status_id = 1 THEN 'Pending'
                       WHEN r.status_id = 2 THEN 'In Progress' 
                       WHEN r.status_id = 3 THEN 'Resolved'
                       ELSE 'Unknown'
                   END as status_name
            FROM reports r 
            WHERE r.report_id = %s AND r.user_id = %s
        ''', (report_id, user_id))
        
        report = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not report:
            return jsonify({'error': 'Report not found'}), 404
            
        # Convert datetime objects to strings for JSON serialization
        if report.get('created_at'):
            report['created_at'] = report['created_at'].strftime('%B %d, %Y at %I:%M %p')
        if report.get('updated_at'):
            report['updated_at'] = report['updated_at'].strftime('%B %d, %Y at %I:%M %p')
            
        return jsonify(report)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/role')
def role():
    users = get_all_users()
    return render_template('1_role_management.html', users=users, roles=["user","admin"])

@app.route('/report')
def report():
    return redirect(url_for('reports.submit_report'))

@app.route('/settings')
@login_required
def settings():
    # Get current user for template
    user_id = session.get('user_id')
    current_user = get_user_by_id(user_id)
    return render_template('5_settings.html', user=current_user)

@app.route('/health')
def health():
    # Health check endpoint for monitoring
    try:
        # Test database connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        cursor.fetchone()
        cursor.close()
        conn.close()
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "timestamp": datetime.now().isoformat()
    }, 200 if db_status == "healthy" else 503

# Temporary as will change images location in future 
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    # Check allowed extensions (security will remove when change to cloud)
    def is_allowed_file(filename):
        ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    if not is_allowed_file(filename):
        abort(400, description="Invalid file type.")

    # Secure filename by not allowing dangerous chars
    safe_filename = secure_filename(filename)
    safe_path = os.path.join(app.root_path, 'uploads')
    return send_from_directory(safe_path, safe_filename)

# custom route to test conn to db, delete after if not needed
@app.route('/test_db.html')
def test_db():
    data = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM test;')
        data = cursor.fetchall()
        db_status = 'Connected to MySQL'
        cursor.close()
        conn.close()
    except Exception as e:
        db_status = f'MySQL connection error: {str(e)}'
    return render_template('test_db.html', db_status=db_status, data=data)

# To hide filename/path
@app.route('/login')
def login():
    return render_template('1_login.html')

@app.route('/register')
def register():
    return render_template('1_register.html')

# This route is the catch-all so u guys don't have to make a specific route for each page everytime, IT HAS TO BE THE LAST ROUTE
# Not secure, if u want a specific page to be secure OR with custom logic, make a new route above
@app.route('/<filename>')
def catch_all(filename):
    print(filename, flush=True)
    return render_template(filename)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')