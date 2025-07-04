import mysql.connector
import os
from flask import (
    Blueprint, abort, current_app, request, session, jsonify
)
import datetime
from flask_wtf.csrf import validate_csrf
from wtforms.validators import ValidationError

bp = Blueprint('admin_dashboard', __name__)

def get_db_connection():
    cfg = current_app.config
    return mysql.connector.connect(
        host=cfg['MYSQL_HOST'],
        user=cfg['MYSQL_USER'],
        password=cfg['MYSQL_PASSWORD'],
        database=cfg['MYSQL_DB'],
    )

def get_statuses():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True) 
    try:
        cursor.execute("SELECT status_id, name FROM status ORDER BY status_id")
        statuses = cursor.fetchall()  
        return statuses
    finally:
        cursor.close()
        conn.close()

def get_all_reports():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT r.report_id, r.title, r.description, r.category_name, r.is_anonymous, r.created_at, s.name AS status_name, u.username
            FROM reports r
            JOIN status s
              ON r.status_id = s.status_id
            LEFT JOIN users u
              ON r.user_id = u.user_id
            ORDER BY r.report_id
        """)
        reports = cursor.fetchall()

        # Override username if anonymous, or supply a placeholder
        for r in reports:
            if r['is_anonymous']:
                r['username'] = 'Anonymous'
            elif r.get('username') is None:
                r['username'] = '—'

        return reports

    finally:
        cursor.close()
        conn.close()

def get_report_attachments(report_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
        SELECT file_name
        FROM report_attachments
        WHERE report_id = %s
        """
        cursor.execute(query, (report_id,))
        results = cursor.fetchall()
        
        return results
    finally:
        cursor.close()
        conn.close()


@bp.route("/update_status", methods=["POST"])
def update_status():
    if session.get("role") != "admin":
        abort(403)

    csrf_token = request.headers.get("X-CSRFToken") or request.headers.get("X-CSRF-Token")
    try:
        validate_csrf(csrf_token)
    except ValidationError:
        return jsonify(success=False, error="Invalid or missing CSRF token"), 400
    
    data = request.get_json()
    # Check if valid integer first
    report_id = is_valid_integer(data.get("report_id"))
    status_id = is_valid_integer(data.get("status_id"))

    if not report_id or not status_id:
        current_app.logger.warning("Invalid or missing report_id/status_id")
        return jsonify(success=False, error="Invalid input."), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE reports
            SET status_id = %s, updated_at = %s
            WHERE report_id = %s
        """, (status_id, datetime.datetime.now(), report_id))
        conn.commit()
        print("Update successful")
        return jsonify(success=True)
    except Exception as e:
        print("Update failed:", e)
        return jsonify(success=False), 500
    finally:
        cursor.close()
        conn.close()

@bp.route("/admin/report_attachments/<int:report_id>", methods=["GET"])
def fetch_report_attachments(report_id):
    attachments = get_report_attachments(report_id)
    return jsonify(attachments)

# Delete Functions

@bp.route("/admin/delete_report/<int:report_id>", methods=["DELETE"])
def delete_report(report_id):
    if session.get("role") != "admin":
        abort(403)

    csrf_token = request.headers.get("X-CSRFToken")
    try:
        validate_csrf(csrf_token)
    except ValidationError:
        return jsonify({"error": "Invalid or missing CSRF token"}), 400
    
    report_id = is_valid_integer(report_id)
    if not report_id:
        return jsonify({"error": "Invalid report ID"}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM report_attachments WHERE report_id = %s", (report_id,))

        cursor.execute("DELETE FROM reports WHERE report_id = %s", (report_id,))
        conn.commit()

        return '', 204 
    except Exception as e:
        current_app.logger.error(f"Failed to delete report {report_id}: {e}")
        return jsonify({"error": "Failed to delete report"}), 500
    finally:
        cursor.close()
        conn.close()

# Validation and Security Functions
def is_valid_integer(val):
    try:
        return int(val)
    except (TypeError, ValueError):
        return None
