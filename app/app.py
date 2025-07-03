from flask import Flask, abort, render_template, redirect, url_for, send_from_directory
from datetime import datetime
import mysql.connector
import os
from report_submission import bp as reports_bp
from home_dashboard import get_report_by_id
from admin_dashboard import get_statuses, get_all_reports
from admin_dashboard import bp as admin_bp
from accounts import bp as accounts_bp
from accounts import get_all_users
from werkzeug.utils import secure_filename
from flask_wtf.csrf import CSRFProtect, generate_csrf


app = Flask(__name__)

# Added CSRF 
csrf = CSRFProtect()
csrf.init_app(app)

# SECRET_KEY (for flash messages & sessions)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_secret_key')

# Initial Configs =================================================
# MySQL configurations
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST', 'mysql')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER', 'x')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD', 'x')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB', 'flask_db')
print("aaa", flush=True)
print(app.config['MYSQL_HOST'],app.config['MYSQL_USER'],app.config['MYSQL_PASSWORD'],app.config['MYSQL_DB'], flush=True)

app.register_blueprint(reports_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(accounts_bp)

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
# Add session check here when done 
def admin():
    statuses = get_statuses()
    reports = get_all_reports()
    return render_template('7_admin_dashboard.html', statuses=statuses, reports=reports)

@app.route('/profile')
# @login_required
def profile():
    """User profile page with reports"""
    # Create dummy user data matching your DB schema
    dummy_user = {
        'user_id': 1,
        'username': 'johndoe',  # Added to match your accounts.py
        'email': 'john.doe@example.com',
        'role': 'user',
        'created_at': datetime.now()
    }
    
    # Create dummy reports data
    dummy_reports = [
        {
            'title': 'Broken Elevator',
            'created_at': datetime(2023, 5, 15),
            'status': 'Pending',
            'category': 'Facilities'
        }
    ]
    
    return render_template('5_profile.html', 
                         current_user=dummy_user,
                         user_reports=dummy_reports)

@app.route('/role')
def role():
    users = get_all_users()
    return render_template('1_role_management.html', users=users, roles=["user","admin"])

@app.route('/report')
def report():
    return redirect(url_for('reports.submit_report'))

@app.route('/settings')
def settings():
    return render_template('5_settings.html')

@app.route('/health')
def health():
    """Health check endpoint for monitoring"""
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

# custom route to test conn to db
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

# This route is the catch-all so u guys don't have to make a specific route for each page everytime, IT HAS TO BE THE LAST ROUTE
# Not secure, if u want a specific page to be secure OR with custom logic, make a new route above
@app.route('/<filename>')
def catch_all(filename):
    print(filename, flush=True)
    return render_template(filename)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

