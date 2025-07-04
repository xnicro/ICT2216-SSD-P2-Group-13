import os
from flask import (
    Blueprint, current_app, flash,
    redirect, render_template, request, session, url_for
)
from werkzeug.utils import secure_filename
import mysql.connector
from flask_wtf.csrf import validate_csrf
from wtforms.validators import ValidationError
from extensions import limiter
from flask_limiter.errors import RateLimitExceeded
# Import the notification function
from user_settings import send_notifications_for_new_report

bp = Blueprint('reports', __name__, template_folder='templates')

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

# Updated mapping to match notification system categories
CATEGORY_MAPPING = {
    'fires': 'fire_hazard',
    'faulty_facilities': 'faulty_equipment',
    'vandalism': 'vandalism',
    'suspicious_activity': 'suspicious_activity',
    'other': 'other_incident'
}

# Display names for UI
CATEGORY_DISPLAY_NAMES = {
    'fires': 'Fires',
    'faulty_facilities': 'Faulty Facilities/Equipment',
    'vandalism': 'Vandalism',
    'suspicious_activity': 'Suspicious Activity',
    'other': 'Others'
}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return (
        '.' in filename and
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    )

def get_db_connection():
    cfg = current_app.config
    return mysql.connector.connect(
        host=cfg['MYSQL_HOST'],
        user=cfg['MYSQL_USER'],
        password=cfg['MYSQL_PASSWORD'],
        database=cfg['MYSQL_DB'],
    )

@bp.route('/report', methods=['GET', 'POST'])
def submit_report():
    if request.method == 'GET':
        return render_template('4_report_submission.html')
    
    # POST: validate CSRF token
    csrf_token = request.form.get("csrf_token")
    try:
        validate_csrf(csrf_token)
    except ValidationError:
        flash("Invalid or missing CSRF token", "error")
        return redirect(url_for('reports.submit_report'))
    
    # ——— POST ———
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    # raw category value from the select
    category_value = request.form.get('category', '')
    # Get the system category name for notifications
    category_system_name = CATEGORY_MAPPING.get(category_value, 'other_incident')
    # Get display name for UI
    category_display_name = CATEGORY_DISPLAY_NAMES.get(category_value, category_value)
    
    is_anon = bool(request.form.get('anonymous'))
    # Only pull category_description if "other" is selected
    category_description = (
        request.form.get('category_description', '').strip()
        if category_value == 'other'
        else None
    )

    # Server-side validation: require a description for "other"
    if category_value == 'other' and not category_description:
        flash('Please provide a short description when you select "Others".', 'danger')
        return render_template('4_report_submission.html',
                               title=title,
                               description=description,
                               selected_category=category_value,
                               category_description=category_description)

    conn = get_db_connection()
    cursor = conn.cursor(buffered=True, dictionary=True)
    try:
        user_id = None if is_anon else session.get('user_id')
        
        # Insert report with both category (for notifications) and category_name (for display)
        cursor.execute("""
            INSERT INTO reports
              (user_id,
               category,
               category_name,
               category_description,
               is_anonymous,
               title,
               description,
               status_id,
               created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, (
            user_id,
            category_system_name,  # For notification system
            category_display_name,  # For display
            category_description,
            int(is_anon),
            title,
            description,
            1  # Default status_id (Pending)
        ))
        report_id = cursor.lastrowid

        # ——— Handle attachments ———
        attachments = []
        for f in request.files.getlist('attachments'):
            if f and allowed_file(f.filename):
                fn = secure_filename(f.filename)
                save_name = f"{report_id}_{fn}"
                save_path = os.path.join(UPLOAD_FOLDER, save_name)
                f.save(save_path)
                attachments.append((report_id, save_name, save_path, f.mimetype))

        if attachments:
            cursor.executemany("""
                INSERT INTO report_attachments
                  (report_id, file_name, file_path, file_type)
                VALUES (%s, %s, %s, %s)
            """, attachments)

        # ——— Commit first to ensure report is saved ———
        conn.commit()
        
        # ——— Send notifications (only for non-anonymous reports) ———
        if not is_anon and user_id:
            try:
                send_notifications_for_new_report(
                    report_id,
                    title,
                    description,
                    category_system_name,
                    user_id
                )
                current_app.logger.info(f"Notifications sent for report {report_id}")
            except Exception as e:
                # Log error but don't fail the report submission
                current_app.logger.error(f"Error sending notifications: {e}")
                # Optionally, you can flash a warning
                flash('Report submitted successfully! (Note: Notifications may not have been sent)', 'warning')
        
        flash('Report submitted successfully!', 'success')
        return redirect(url_for('index'))

    except Exception as e:
        conn.rollback()
        current_app.logger.error("Error submitting report: %s", e)
        flash('An error occurred while submitting your report. Please try again.', 'error')
        return redirect(url_for('reports.submit_report'))

    finally:
        cursor.close()
        conn.close()