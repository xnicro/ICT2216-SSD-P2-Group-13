from flask import Flask, abort, render_template, redirect, url_for, send_from_directory, session, flash, request, \
    jsonify
from datetime import datetime
from datetime import timedelta
import mysql.connector
import os
import re
from datetime import datetime
from flask import make_response
from report_submission import bp as reports_bp
from home_dashboard import get_report_by_id, get_report_attachments
from admin_dashboard import get_statuses, get_all_reports
from admin_dashboard import bp as admin_bp
from accounts import bp as accounts_bp
from admin_settings import admin_settings_bp
from accounts import get_all_users
from werkzeug.utils import secure_filename
from functools import wraps
from flask_wtf.csrf import CSRFProtect, generate_csrf
from extensions import limiter
from access_control import ROLE_PERMISSIONS, ROLE_REDIRECT_MAP, permission_required, login_required, otp_verified_required, role_required

# Import logging configuration
from logging_config import setup_graylog_logging, log_security_event, log_application_event, log_database_event

app = Flask(__name__)

# Setup Graylog logging early
setup_graylog_logging(app)

limiter.init_app(app)

csrf = CSRFProtect()
csrf.init_app(app)

# SECRET_KEY (for flash messages & sessions)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_secret_key')
csrf = CSRFProtect(app)

# Secure session configuration
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,  # Prevent JS access to session cookie
    SESSION_COOKIE_SECURE=not app.debug,  # Only allow over HTTPS in production
    SESSION_COOKIE_SAMESITE='Lax',  # Helps mitigate CSRF (can use 'Strict' if no third-party use)
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=30)  # Session timeout duration
)

# Initial Configs =================================================
# MySQL configurations
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST', 'mysql')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER', 'x')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD', 'x')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB', 'flask_db')

# Email configuration for notifications
app.config['SMTP_SERVER'] = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
app.config['SMTP_PORT'] = int(os.getenv('SMTP_PORT', 587))
app.config['SENDER_EMAIL'] = os.getenv('SENDER_EMAIL', 'your-app@example.com')
app.config['SENDER_PASSWORD'] = os.getenv('SENDER_PASSWORD', 'your-app-password')
app.config['APP_NAME'] = os.getenv('APP_NAME', 'Your App Name')

# Log application startup
log_application_event("application_startup", details={"app_name": app.config['APP_NAME']})

# Register blueprints
app.register_blueprint(reports_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(accounts_bp)
app.register_blueprint(admin_settings_bp)

# Import and register notification system blueprint
try:
    from user_settings import settings_bp

    app.register_blueprint(settings_bp)
    app.logger.info("Settings blueprint registered successfully")
    log_application_event("blueprint_registered", details={"blueprint": "settings"})
except ImportError as e:
    app.logger.warning(f"Could not import settings blueprint: {e}")
    log_application_event("blueprint_registration_failed", level="warning",
                          details={"blueprint": "settings", "error": str(e)})


@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=generate_csrf())


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}


def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=app.config['MYSQL_HOST'],
            user=app.config['MYSQL_USER'],
            password=app.config['MYSQL_PASSWORD'],
            database=app.config['MYSQL_DB']
        )
        return conn
    except Exception as e:
        app.logger.error(f"Database connection failed: {e}")
        log_database_event("connection_failed", details={"error": str(e)})
        raise


# Helper function to get user by ID
def get_user_by_id(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE user_id = %s', (user_id,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        log_database_event("user_query", table="users", user_id=user_id)
        return user
    except Exception as e:
        app.logger.error(f"Error getting user: {e}")
        log_database_event("user_query_failed", table="users", user_id=user_id, details={"error": str(e)})
        return None


# Helper function to get user reports
def get_user_reports(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

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

        app.logger.info(f"Found {len(reports)} reports for user_id {user_id}")
        log_database_event("user_reports_query", table="reports", user_id=user_id, details={"count": len(reports)})
        return reports
    except Exception as e:
        app.logger.error(f"Error getting user reports: {e}")
        log_database_event("user_reports_query_failed", table="reports", user_id=user_id, details={"error": str(e)})
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
        app.logger.error(f"Error getting notification count: {e}")
        log_database_event("notification_count_failed", table="notification", user_id=user_id,
                           details={"error": str(e)})
        return 0


# Context processor to inject notification count
@app.context_processor
def inject_notification_count():
    """Inject unread notification count into all templates"""
    if 'user_id' in session:
        notification_count = get_unread_notification_count(session['user_id'])
        return dict(notification_count=notification_count)
    return dict(notification_count=0)


# Helper function to check if path should be logged
def should_log_request(path):
    """Check if request should be logged (filter out static files and frequent endpoints)"""
    skip_paths = [
        '/static/',
        '/favicon.ico',
        '/robots.txt',
        '/health'  # Remove if you want to log health checks
    ]

    for skip_path in skip_paths:
        if path.startswith(skip_path):
            return False

    return True


# Request logging middleware
@app.before_request
def log_request_info():
    """Log incoming requests (filtered)"""
    if not should_log_request(request.path):
        return

    user_id = session.get('user_id')
    log_application_event(
        "request_received",
        details={
            "method": request.method,
            "path": request.path,
            "remote_addr": request.remote_addr,
            "user_agent": request.headers.get('User-Agent', ''),
            "referrer": request.referrer
        },
        user_id=user_id
    )


@app.after_request
def log_response_info(response):
    """Log response information (filtered)"""
    if not should_log_request(request.path):
        return response

    user_id = session.get('user_id')

    # Log errors and important status codes
    if response.status_code >= 400:
        level = "error" if response.status_code >= 500 else "warning"
        log_application_event(
            "request_completed",
            level=level,
            details={
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "remote_addr": request.remote_addr
            },
            user_id=user_id
        )

    return response

@app.after_request
def add_security_headers(response):
    # Basic security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    
    # Allow our resources
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' cdnjs.cloudflare.com cdn.jsdelivr.net 'unsafe-inline'; "
        "style-src 'self' cdnjs.cloudflare.com fonts.googleapis.com cdn-uicons.flaticon.com cdn.jsdelivr.net 'unsafe-inline'; "
        "font-src 'self' cdnjs.cloudflare.com fonts.gstatic.com cdn-uicons.flaticon.com cdn.jsdelivr.net data:; "
        "img-src 'self' data: cdn-uicons.flaticon.com cdn.jsdelivr.net; "
        "connect-src 'self'; "
        "frame-src 'none'; "
        "object-src 'none'"
    )
    return response

# App routes ============================================================
@app.route('/')
@login_required
@role_required('user')
def index():
    log_application_event("index_accessed", user_id=session.get('user_id'))
    reports = get_all_reports()
    response = make_response(render_template('0_index.html', reports=reports))
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response



@app.route('/report/<int:report_id>')
@login_required
@role_required('user')
def view_report(report_id):
    log_application_event("report_viewed", user_id=session.get('user_id'), details={"report_id": report_id})
    report = get_report_by_id(report_id)
    if not report:
        log_application_event("report_not_found", level="warning", user_id=session.get('user_id'),
                              details={"report_id": report_id})
        return "Report not found", 404
    return render_template('0_report_detail.html', report=report)

@app.route("/report_attachments/<int:report_id>", methods=["GET"])
@login_required
@role_required('user')
def fetch_report_attachments(report_id):
    attachments = get_report_attachments(report_id)
    return jsonify(attachments)


@app.route('/admin')
@login_required
@otp_verified_required
@role_required('admin')
def admin():
    log_security_event("admin_dashboard_accessed", user_id=session.get('user_id'), request=request)
    statuses = get_statuses()
    reports = get_all_reports()
    return render_template('7_admin_dashboard.html', statuses=statuses, reports=reports)


@app.route('/profile')
@login_required
@otp_verified_required
@role_required('user')
def profile():
    """User profile page with real user data and reports"""
    user_id = session.get('user_id')
    log_application_event("profile_accessed", user_id=user_id)

    # Get current user data
    current_user = get_user_by_id(user_id)
    if not current_user:
        log_security_event("profile_user_not_found", user_id=user_id, request=request)
        flash('User not found', 'error')
        return render_template('1_login.html')

    # Get user's reports
    user_reports = get_user_reports(user_id)

    response = make_response(render_template('5_profile.html',
                                             current_user=current_user,
                                             user_reports=user_reports))
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response



@app.route('/update_profile', methods=['POST'])
@login_required
@role_required('user')
@permission_required('update_profile')
def update_profile():
    """Update user profile information with comprehensive validation"""
    user_id = session.get('user_id')
    log_security_event("profile_update_attempt", user_id=user_id, request=request)

    try:
        # Get form data
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()

        # INPUT VALIDATION - FSR 4
        validation_errors = []

        # Basic field validation
        if not username:
            validation_errors.append("Username is required")
        if not email:
            validation_errors.append("Email is required")

        # Username validation
        if username:
            if len(username) < 3:
                validation_errors.append("Username must be at least 3 characters long")
            if len(username) > 50:
                validation_errors.append("Username must be less than 50 characters")
            if not re.match(r'^[a-zA-Z0-9_.-]+$', username):
                validation_errors.append("Username can only contain letters, numbers, dots, hyphens, and underscores")

        # Email validation - Comprehensive check
        if email:
            # Basic email pattern validation
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                validation_errors.append("Please enter a valid email address (e.g., user@example.com)")

            # Additional email checks
            if len(email) > 254:  # RFC 5321 limit
                validation_errors.append("Email address is too long")

            # Check for valid domain part
            if '@' in email:
                local_part, domain_part = email.rsplit('@', 1)

                # Local part validation
                if len(local_part) > 64:  # RFC 5321 limit
                    validation_errors.append("Email username part is too long")
                if not local_part:
                    validation_errors.append("Email must have a username before @")

                # Domain part validation
                if not domain_part:
                    validation_errors.append("Email must have a domain after @")
                elif not re.match(r'^[a-zA-Z0-9.-]+$', domain_part):
                    validation_errors.append("Email domain contains invalid characters")
                elif domain_part.startswith('.') or domain_part.endswith('.'):
                    validation_errors.append("Email domain cannot start or end with a dot")
                elif '..' in domain_part:
                    validation_errors.append("Email domain cannot have consecutive dots")
                elif not '.' in domain_part:
                    validation_errors.append("Email domain must contain at least one dot")

        # Show validation errors if any
        if validation_errors:
            log_security_event("profile_update_validation_failed", user_id=user_id,
                               details={"errors": validation_errors}, request=request)
            for error in validation_errors:
                flash(error, 'error')
            return redirect(url_for('profile'))

        # Check for duplicate username/email in database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if username already exists (excluding current user)
        cursor.execute('SELECT user_id FROM users WHERE username = %s AND user_id != %s', (username, user_id))
        if cursor.fetchone():
            log_security_event("profile_update_duplicate_username", user_id=user_id,
                               details={"username": username}, request=request)
            flash('Username already exists. Please choose a different username.', 'error')
            cursor.close()
            conn.close()
            return redirect(url_for('profile'))

        # Check if email already exists (excluding current user)
        cursor.execute('SELECT user_id FROM users WHERE email = %s AND user_id != %s', (email, user_id))
        if cursor.fetchone():
            log_security_event("profile_update_duplicate_email", user_id=user_id,
                               details={"email": email}, request=request)
            flash('Email address already exists. Please use a different email.', 'error')
            cursor.close()
            conn.close()
            return redirect(url_for('profile'))

        # Sanitize inputs to prevent XSS attacks
        import html
        username = html.escape(username)
        email = html.escape(email)

        # Update user in database
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

        # Log successful security event
        log_security_event("profile_updated_successfully", user_id=user_id,
                           details={"username": username, "email": email}, request=request)
        log_database_event("profile_updated", table="users", user_id=user_id,
                           details={"username": username, "email": email})

    except Exception as e:
        flash('Error updating profile. Please try again.', 'error')
        # Log detailed error
        app.logger.error(f"Profile update error for user {user_id}: {str(e)}")
        log_security_event("profile_update_error", user_id=user_id,
                           details={"error": str(e)}, request=request)

    return redirect(url_for('profile'))


@app.route('/change_password', methods=['POST'])
@login_required
@role_required('user')
@permission_required('change_password')
def change_password():
    """Change user password with strong security validation"""
    user_id = session.get('user_id')
    log_security_event("password_change_attempt", user_id=user_id, request=request)

    try:
        # Get form data
        current_password = request.form.get('currentPassword', '').strip()
        new_password = request.form.get('newPassword', '').strip()
        confirm_password = request.form.get('confirmPassword', '').strip()

        # Basic validation
        if not current_password or not new_password or not confirm_password:
            log_security_event("password_change_missing_fields", user_id=user_id, request=request)
            flash('All password fields are required', 'error')
            return redirect(url_for('profile'))

        # PASSWORD SECURITY VALIDATION
        password_errors = []

        # Minimum length check
        if len(new_password) < 8:
            password_errors.append("at least 8 characters")

        # Uppercase letter check
        if not re.search(r'[A-Z]', new_password):
            password_errors.append("at least one uppercase letter (A-Z)")

        # Lowercase letter check
        if not re.search(r'[a-z]', new_password):
            password_errors.append("at least one lowercase letter (a-z)")

        # Number check
        if not re.search(r'\d', new_password):
            password_errors.append("at least one number (0-9)")

        # Special character check
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', new_password):
            password_errors.append("at least one special character (!@#$%^&*(),.?\":{}|<>)")

        # Check if passwords match
        if new_password != confirm_password:
            password_errors.append("passwords must match")

        # Check if new password is same as current password
        if current_password == new_password:
            password_errors.append("new password must be different from current password")

        # If there are password validation errors, show them
        if password_errors:
            log_security_event("password_change_validation_failed", user_id=user_id,
                               details={"errors": password_errors}, request=request)
            if len(password_errors) == 1:
                flash(f'Password must have {password_errors[0]}.', 'error')
            else:
                error_msg = "Password must have: " + ", ".join(password_errors[:-1]) + f", and {password_errors[-1]}."
                flash(error_msg, 'error')
            return redirect(url_for('profile'))

        # Get current user data to verify current password
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE user_id = %s', (user_id,))
        user = cursor.fetchone()

        if not user:
            log_security_event("password_change_user_not_found", user_id=user_id, request=request)
            flash('User not found', 'error')
            cursor.close()
            conn.close()
            return redirect(url_for('profile'))

        # Import password hasher
        from accounts import ph
        from argon2.exceptions import VerifyMismatchError

        # Verify current password
        try:
            ph.verify(user['pwd'], current_password)
        except VerifyMismatchError:
            log_security_event("password_change_wrong_current_password", user_id=user_id, request=request)
            flash('Current password is incorrect', 'error')
            cursor.close()
            conn.close()
            return redirect(url_for('profile'))
        except Exception as e:
            log_security_event("password_change_verify_error", user_id=user_id,
                               details={"error": str(e)}, request=request)
            flash('Error verifying current password', 'error')
            cursor.close()
            conn.close()
            return redirect(url_for('profile'))

        # Hash new password securely
        new_hashed_password = ph.hash(new_password)

        # Update password in database
        cursor.execute('''
            UPDATE users 
            SET pwd = %s
            WHERE user_id = %s
        ''', (new_hashed_password, user_id))
        conn.commit()
        cursor.close()
        conn.close()

        flash('Password changed successfully! Please use your new password for future logins.', 'success')

        # Log successful security event
        log_security_event("password_changed_successfully", user_id=user_id, request=request)
        log_database_event("password_updated", table="users", user_id=user_id)

    except Exception as e:
        flash('Error changing password. Please try again.', 'error')
        # Log detailed error
        app.logger.error(f"Password change error for user {user_id}: {str(e)}")
        log_security_event("password_change_error", user_id=user_id,
                           details={"error": str(e)}, request=request)

    return redirect(url_for('profile'))


@app.route('/api/report/<int:report_id>')
@login_required
@role_required('user')
def get_report_details(report_id):
    """Get report details for the modal"""
    user_id = session.get('user_id')
    log_application_event("api_report_details_accessed", user_id=user_id, details={"report_id": report_id})

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get report details - ensure user owns this report
        cursor.execute('''
            SELECT r.*, s.name AS status_name
            FROM reports r 
            JOIN status s ON r.status_id = s.status_id
            WHERE r.report_id = %s AND r.user_id = %s
        ''', (report_id, user_id))

        report = cursor.fetchone()
        cursor.close()
        conn.close()

        if not report:
            log_application_event("api_report_not_found", level="warning", user_id=user_id,
                                  details={"report_id": report_id})
            return jsonify({'error': 'Report not found'}), 404

        # Convert datetime objects to strings for JSON serialization
        if report.get('created_at'):
            report['created_at'] = report['created_at'].strftime('%B %d, %Y at %I:%M %p')
        if report.get('updated_at'):
            report['updated_at'] = report['updated_at'].strftime('%B %d, %Y at %I:%M %p')

        log_application_event("api_report_details_success", user_id=user_id, details={"report_id": report_id})
        return jsonify(report)

    except Exception as e:
        app.logger.error(f"API report details error: {str(e)}")
        log_application_event("api_report_details_error", level="error", user_id=user_id,
                              details={"report_id": report_id, "error": str(e)})
        return jsonify({'error': str(e)}), 500


@app.route('/role')
@login_required
@role_required('superadmin')
def role():
    log_security_event("role_management_accessed", user_id=session.get('user_id'), request=request)
    users = get_all_users()
    return render_template('1_role_management.html', users=users, roles=["user", "admin"])


@app.route('/report')
@login_required
@role_required('user')
@permission_required('submit_report')
def report():
    log_application_event("report_page_accessed", user_id=session.get('user_id'))
    return redirect(url_for('reports.submit_report'))


@app.route('/settings')
@login_required
def settings():
    user_id = session.get('user_id')
    log_application_event("settings_accessed", user_id=user_id)
    current_user = get_user_by_id(user_id)

    # Check if user has admin-level permission
    allowed_permissions = ROLE_PERMISSIONS.get(current_user.get('role'), [])

    if 'update_admin_settings' in allowed_permissions:
        log_security_event("admin_settings_accessed", user_id=user_id, request=request)
        return render_template('5_admin_settings.html', user=current_user)
    elif 'update_user_settings' in allowed_permissions:
        return render_template('5_user_settings.html', user=current_user)
    else:
        log_security_event("settings_access_denied", user_id=user_id, request=request)
        abort(403)


@app.route('/delete_account', methods=['POST'])
@login_required
@role_required('user')
def delete_account():
    """Delete user account and all associated data"""
    user_id = session.get('user_id')
    log_security_event("account_deletion_attempt", user_id=user_id, request=request)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Start transaction to ensure data integrity
        cursor.execute('START TRANSACTION')

        # Delete user's report attachments first (if any exist)
        cursor.execute('''
            DELETE FROM report_attachments 
            WHERE report_id IN (SELECT report_id FROM reports WHERE user_id = %s)
        ''', (user_id,))

        # Delete user's reports
        cursor.execute('DELETE FROM reports WHERE user_id = %s', (user_id,))

        # Delete user's notifications (if you have this table)
        try:
            cursor.execute('DELETE FROM notification WHERE user_id = %s', (user_id,))
        except:
            # Table might not exist, ignore error
            pass

        # Finally delete the user
        cursor.execute('DELETE FROM users WHERE user_id = %s', (user_id,))

        # Commit all changes
        conn.commit()
        cursor.close()
        conn.close()

        # Log successful deletion
        log_security_event("account_deleted_successfully", user_id=user_id, request=request)
        log_database_event("account_deleted", table="users", user_id=user_id)

        # Clear the session
        session.clear()

        flash('Your account has been successfully deleted. We\'re sorry to see you go!', 'success')
        return redirect(url_for('login'))

    except Exception as e:
        # Rollback on any error
        try:
            conn.rollback()
            cursor.close()
            conn.close()
        except:
            pass

        app.logger.error(f"Error deleting account: {e}")
        log_security_event("account_deletion_error", user_id=user_id,
                           details={"error": str(e)}, request=request)
        flash(f'Error deleting account: {str(e)}', 'error')
        return redirect(url_for('profile'))


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
        log_application_event("health_check_failed", level="error", details={"db_status": db_status})

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
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    if not is_allowed_file(filename):
        log_security_event("file_upload_invalid_extension",
                           details={"filename": filename}, request=request)
        abort(400, description="Invalid file type.")

    # Secure filename by not allowing dangerous chars
    safe_filename = secure_filename(filename)
    safe_path = os.path.join(app.root_path, 'uploads')
    log_application_event("file_served", details={"filename": safe_filename})
    return send_from_directory(safe_path, safe_filename)


# custom route to test conn to db, delete after if not needed
@app.route('/test_db.html')
def test_db():
    log_application_event("test_db_accessed")
    data = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM test;')
        data = cursor.fetchall()
        db_status = 'Connected to MySQL'
        cursor.close()
        conn.close()
        log_application_event("test_db_success", details={"status": db_status})
    except Exception as e:
        db_status = f'MySQL connection error: {str(e)}'
        log_application_event("test_db_failed", level="error", details={"status": db_status})
    return render_template('test_db.html', db_status=db_status, data=data)


# To hide filename/path
@app.route('/login')
def login():
    log_application_event("login_page_accessed")
    if 'user_id' in session:
        if not session.get('verified', False):
            return redirect(url_for('accounts.verify_otp'))
        role = session.get('role')
        default_route = ROLE_REDIRECT_MAP.get(role, 'profile')
        log_application_event("login_already_authenticated", user_id=session.get('user_id'))
        flash("You are already logged in.", "info")
        return redirect(url_for(default_route))
    
    response = make_response(render_template('1_login.html'))
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response




@app.route('/register')
def register():
    log_application_event("register_page_accessed")
    if 'user_id' in session:
        if not session.get('verified', False):
            return redirect(url_for('accounts.verify_otp'))
        role = session.get('role')
        default_route = ROLE_REDIRECT_MAP.get(role, 'profile')
        log_application_event("login_already_authenticated", user_id=session.get('user_id'))
        flash("You are already logged in.", "info")
        return redirect(url_for(default_route))
    
    response = make_response(render_template('1_register.html'))
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response




# Error handlers with logging
@app.errorhandler(404)
def not_found(error):
    log_application_event("404_error", level="warning",
                          details={"path": request.path, "remote_addr": request.remote_addr})
    return render_template('errors/404.html'), 404


@app.errorhandler(403)
def forbidden(error):
    log_security_event("403_error", user_id=session.get('user_id'),
                       details={"path": request.path}, request=request)
    return render_template('errors/403.html'), 403


@app.errorhandler(500)
def internal_error(error):
    log_application_event("500_error", level="error",
                          details={"path": request.path, "error": str(error)})
    return render_template('errors/500.html'), 500


@app.route('/test-docker-logs')
def test_docker_logs():
    """Test route for Docker logging"""
    app.logger.info("Testing from Docker container", extra={
        'event_type': 'docker_container_test',
        'container': 'flask_app'
    })

    log_application_event("docker_app_test", details={
        "message": "Hello from Flask in Docker!",
        "container": "flask_app"
    })

    log_security_event("docker_security_test",
                       user_id=session.get('user_id'),
                       details={"test_type": "docker_logging"},
                       request=request)

    return "Docker logs sent! Check Graylog for: event_type:docker_*"


if __name__ == '__main__':
    log_application_event("application_started", details={"debug": True, "host": "0.0.0.0"})
    app.run(debug=True, host='0.0.0.0')