from flask import session, abort, flash, render_template, abort
from functools import wraps

ROLE_PERMISSIONS = {
    'user': ['view_all_reports', 'view_report_attachments', 'submit_report', 
             'update_profile', 'change_password', 'update_user_settings'],
    'admin': ['view_all_reports','view_report_attachments', 'manage_reports', 
              'update_admin_settings'],
    'superadmin': ['manage_roles']
}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return render_template('1_login.html')
        return f(*args, **kwargs)
    return decorated_function

def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'role' not in session:
                flash('Unauthorized access.', 'error')
                return render_template('1_login.html')

            if session['role'] not in allowed_roles:
                abort(403)

            return f(*args, **kwargs)
        return decorated_function
    return decorator

def permission_required(*required_permissions):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            role = session.get('role')
            if not role:
                abort(403)
            allowed_permissions = ROLE_PERMISSIONS.get(role, [])
            if not any(perm in allowed_permissions for perm in required_permissions):
                abort(403)
            return f(*args, **kwargs)
        return wrapper
    return decorator
