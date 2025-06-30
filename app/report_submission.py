import os
from flask import (
    Blueprint, current_app, flash,
    redirect, render_template, request, session, url_for
)
from werkzeug.utils import secure_filename
import mysql.connector

bp = Blueprint('reports', __name__, template_folder='templates')

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
# Mapping of form values to their display names
CATEGORY_MAPPING = {
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

    # ——— POST ———
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    # raw category value from the select
    category_value = request.form.get('category', '')
    # lookup human-readable label
    category_name = CATEGORY_MAPPING.get(category_value, category_value)
    is_anon = bool(request.form.get('anonymous'))
    # Only pull category_description if “other” is selected
    category_description = (
        request.form.get('category_description', '').strip()
        if category_value == 'other'
        else None
    )

    # Server-side validation: require a description for “other”
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
        # insert using the human-readable category_name
        cursor.execute("""
            INSERT INTO reports
              (user_id,
               category_name,
               category_description,
               is_anonymous,
               title,
               description)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            user_id,
            category_name,
            category_description,
            int(is_anon),
            title,
            description
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

        # ——— Commit & finish ———
        conn.commit()
        flash('Report submitted successfully!', 'success')
        return redirect(url_for('index'))

    except Exception as e:
        conn.rollback()
        current_app.logger.error("Error submitting report: %s", e)
        raise

    finally:
        cursor.close()
        conn.close()
