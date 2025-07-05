import os
import re
from flask import (
    Blueprint, abort, current_app, flash, jsonify,
    redirect, render_template, request, session, url_for
)
from werkzeug.utils import secure_filename
import mysql.connector
from flask_wtf.csrf import validate_csrf
from wtforms.validators import ValidationError
from extensions import limiter
from flask_limiter.errors import RateLimitExceeded
from user_settings import send_notifications_for_new_report

bp = Blueprint('reports', __name__, template_folder='templates')

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

CATEGORY_DISPLAY_NAMES = {
    'fires': 'Fires',
    'faulty_facilities': 'Faulty Facilities/Equipment',
    'vandalism': 'Vandalism',
    'suspicious_activity': 'Suspicious Activity',
    'other': 'Others'
}

MAX_TITLE_LENGTH = 255
MAX_DESCRIPTION_LENGTH = 1000
MAX_CATEGORY_DESCRIPTION_LENGTH = 255

MAX_ATTACHMENTS_PER_REPORT = 5
MAX_TOTAL_UPLOAD_SIZE_MB = 5

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Helper function to check if the request is an AJAX request
def is_ajax_request():
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json

def contains_invalid_chars(value):
    if re.search(r'<script\b[^>]*>.*?</script>', value, re.IGNORECASE):
        return True
    if re.search(r'onerror=|onload=|javascript:|data:text/html', value, re.IGNORECASE):
        return True
    if re.search(r'SELECT\s|\sFROM\s|\sINSERT\s|\sUPDATE\s|\sDELETE\s|\sOR\s|\sAND\s|\sUNION\s|\sEXEC\s', value, re.IGNORECASE):
        return True
    if '<' in value or '>' in value: # Basic check for unescaped HTML tags
        return True
    if re.search(r'[\x00-\x1F\x7F-\x9F]', value): # Control characters
        return True
    return False

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
@limiter.limit("5 per minute")
def submit_report():
    if session.get("role") != "user":
        if is_ajax_request():
            return jsonify({"message": "Unauthorized access", "error_messages": ["Unauthorized access"]}), 403
        abort(403)

    title = ''
    description = ''
    selected_category = ''
    category_description = ''
    is_anon = False

    if request.method == 'GET':
        return render_template('4_report_submission.html',
                               title=title,
                               description=description,
                               selected_category=selected_category,
                               category_description=category_description,
                               is_anonymous=is_anon)

    csrf_token = request.form.get("csrf_token")
    try:
        validate_csrf(csrf_token)
    except ValidationError:
        if is_ajax_request():
            return jsonify({"message": "Invalid or missing CSRF token", "error_messages": ["Invalid or missing CSRF token"]}), 400
        flash("Invalid or missing CSRF token", "error")
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        selected_category = request.form.get('category', '')
        category_description = (
            request.form.get('category_description', '').strip()
            if selected_category == 'other'
            else ''
        )
        is_anon = bool(request.form.get('anonymous'))
        return render_template('4_report_submission.html',
                               title=title,
                               description=description,
                               selected_category=selected_category,
                               category_description=category_description,
                               is_anonymous=is_anon)

    # Get raw values for contains_invalid_chars check (before stripping)
    # IMPORTANT: Your current code was directly using stripped values for contains_invalid_chars
    # which is not ideal. It should use raw values for that check.
    # Let's align this with the previous suggestion.
    raw_title = request.form.get('title', '')
    raw_description = request.form.get('description', '')
    raw_category_description = request.form.get('category_description', '') if request.form.get('category', '') == 'other' else ''


    # Get trimmed values for emptiness and length checks (used for database storage as well)
    title = raw_title.strip()
    description = raw_description.strip()
    category_value = request.form.get('category', '')
    is_anon = bool(request.form.get('anonymous'))

    category_description = raw_category_description.strip() # Trim here for storage/display


    validation_errors = []

    if not title:
        validation_errors.append("Title cannot be empty.")
    # No "else" here, so it continues to check length even if empty (but on empty string length is 0, so fine)
    if title and not (1 <= len(title) <= MAX_TITLE_LENGTH): # Only check length if title is not empty after trimming
        validation_errors.append(f"Title must be between 1 and {MAX_TITLE_LENGTH} characters.")

    if not description:
        validation_errors.append("Description cannot be empty.")
    if description and not (1 <= len(description) <= MAX_DESCRIPTION_LENGTH): # Only check length if description is not empty after trimming
        validation_errors.append(f"Description must be between 1 and {MAX_DESCRIPTION_LENGTH} characters.")

    if category_value not in CATEGORY_DISPLAY_NAMES:
        validation_errors.append("Invalid report category selected.")
    elif not category_value: # This case is probably caught by the first if for invalid category
        validation_errors.append("Please select a category.")

    category_display_name = CATEGORY_DISPLAY_NAMES.get(category_value)

    if category_value == 'other':
        if not category_description:
            validation_errors.append('Category description cannot be empty.')
        # Ensure length check only applies if category_description is not empty
        elif not (1 <= len(category_description) <= MAX_CATEGORY_DESCRIPTION_LENGTH):
            validation_errors.append(f"Category description must be between 1 and {MAX_CATEGORY_DESCRIPTION_LENGTH} characters.")

    invalid_char_fields = []
    # Use raw_values for contains_invalid_chars check
    if contains_invalid_chars(raw_title):
        invalid_char_fields.append('Title')
    if contains_invalid_chars(raw_description):
        invalid_char_fields.append('Description')
    if raw_category_description and contains_invalid_chars(raw_category_description): # Only check if raw_category_description was provided
        invalid_char_fields.append('Category description')

    if invalid_char_fields:
        if len(invalid_char_fields) == 1:
            validation_errors.append(f"{invalid_char_fields[0]} contains invalid characters.")
        elif len(invalid_char_fields) == 2:
            validation_errors.append(f"{invalid_char_fields[0]} and {invalid_char_fields[1]} contain invalid characters.")
        else:
            fields_str = ", ".join(invalid_char_fields[:-1]) + f" and {invalid_char_fields[-1]}"
            validation_errors.append(f"{fields_str} contain invalid characters.")

    if validation_errors:
        current_app.logger.debug(f"Validation errors detected (server): {validation_errors}")
        if is_ajax_request():
            return jsonify({"message": "Validation failed", "error_messages": validation_errors}), 400
        for error_msg in validation_errors:
            flash(error_msg, 'error')
        return render_template('4_report_submission.html',
                               title=title,
                               description=description,
                               selected_category=category_value,
                               category_description=category_description,
                               is_anonymous=is_anon)

    conn = get_db_connection()
    cursor = conn.cursor(buffered=True, dictionary=True)
    try:
        user_id = None if is_anon else session.get('user_id')

        cursor.execute("""
            INSERT INTO reports
              (user_id,
               category_name,
               category_description,
               is_anonymous,
               title,
               description,
               status_id,
               created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        """, (
            user_id,
            category_display_name,
            category_description,
            int(is_anon),
            title, # Use trimmed title for database
            description, # Use trimmed description for database
            1
        ))
        report_id = cursor.lastrowid

        attachments = []
        uploaded_files_count = 0
        total_upload_size = 0

        for f in request.files.getlist('attachments'):
            if not f or f.filename == '':
                continue

            uploaded_files_count += 1
            if uploaded_files_count > MAX_ATTACHMENTS_PER_REPORT:
                flash(f"You can only upload a maximum of {MAX_ATTACHMENTS_PER_REPORT} files.", 'error')
                break 

            f.seek(0, os.SEEK_END)
            file_size = f.tell()
            f.seek(0)

            total_upload_size += file_size
            if total_upload_size > MAX_TOTAL_UPLOAD_SIZE_MB * 1024 * 1024:
                if is_ajax_request():
                    conn.rollback()
                    return jsonify({
                        "message": "Upload size limit exceeded",
                        "error_messages": [f"Total upload size exceeds the maximum allowed of {MAX_TOTAL_UPLOAD_SIZE_MB}MB. Please reduce the number of files and try again."]
                    }), 400
                flash(
                    f"Total upload size exceeds the maximum allowed of {MAX_TOTAL_UPLOAD_SIZE_MB}MB. Please reduce the number of files and try again.",
                    'error'
                    )
                break

            if allowed_file(f.filename):
                fn = secure_filename(f.filename)
                save_name = f"{report_id}_{fn}"
                save_path = os.path.join(UPLOAD_FOLDER, save_name)

                try:
                    f.save(save_path)
                    attachments.append((report_id, save_name, save_path, f.mimetype))
                except Exception as e:
                    current_app.logger.error(f"Error saving file {fn}: {e}")
                    if is_ajax_request():
                        conn.rollback()
                        return jsonify({"message": f"Failed to save file '{fn}'.", "error_messages": [f"Failed to save file '{fn}'. Please try again."]})
                    flash(f"Failed to save file '{fn}'. Please try again.", 'error')
            else:
                if is_ajax_request():
                    conn.rollback()
                    return jsonify({"message": f"Unsupported file type for '{f.filename}'.", "error_messages": [f"File '{f.filename}' has an unsupported file type. Allowed types are {', '.join(ALLOWED_EXTENSIONS)}."]})
                flash(f"File '{f.filename}' has an unsupported file type. Allowed types are {', '.join(ALLOWED_EXTENSIONS)}.", 'error')

        if attachments:
            cursor.executemany("""
                INSERT INTO report_attachments
                  (report_id, file_name, file_path, file_type)
                VALUES (%s, %s, %s, %s)
            """, attachments)

        conn.commit()

        if not is_anon and user_id:
            try:
                send_notifications_for_new_report(
                    report_id,
                    title,
                    description,
                    category_display_name,
                    user_id
                )
                current_app.logger.info(f"Notifications sent for report {report_id}")
            except Exception as e:
                current_app.logger.error(f"Error sending notifications for report {report_id}: {e}")

        if is_ajax_request():
            return jsonify({"message": "Report submitted successfully!", "redirect": url_for('index')}), 200
        flash('Report submitted successfully!', 'success')
        return redirect(url_for('index'))

    except Exception as e:
        conn.rollback()
        current_app.logger.error("Error submitting report: %s", e)
        if is_ajax_request():
            return jsonify({"message": "An error occurred while submitting your report.", "error_messages": ["An error occurred while submitting your report. Please try again."]}), 500
        flash('An error occurred while submitting your report. Please try again.', 'error')
        return render_template('4_report_submission.html',
                               title=title,
                               description=description,
                               selected_category=category_value,
                               category_description=category_description,
                               is_anonymous=is_anon)

    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

@bp.errorhandler(RateLimitExceeded)
def rate_limit_exceeded(e):
    retry_after = int(e.description.split(" ")[-1]) if "second" in str(e.description) else 60 
    flash("You are submitting too many reports. Please try again in a few minutes.", "error")
    return render_template('4_report_submission.html',
                           title=request.form.get('title', '').strip(),
                           description=request.form.get('description', '').strip(),
                           selected_category=request.form.get('category', ''),
                           category_description=(request.form.get('category_description', '').strip()
                                                 if request.form.get('category', '') == 'other' else ''),
                           is_anonymous=bool(request.form.get('anonymous')), rate_limited=True, retry_after=retry_after), 429