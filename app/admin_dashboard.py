# I MUST ADD ACCESS CONTROL SUCH AS SESSION.GET(ADMIN) OR SMT FOR ALL FUNCTIONS IN FUTURE
import mysql.connector
import os
from flask import (
    Blueprint, current_app, request, session, jsonify
)
import datetime

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
        query = """
        SELECT r.report_id, r.title, r.category_name, s.name AS status_name
        FROM reports r
        JOIN status s ON r.status_id = s.status_id
        ORDER BY r.report_id
        """
        cursor.execute(query)
        reports = cursor.fetchall()
        return reports
    finally:
        cursor.close()
        conn.close()

@bp.route("/update_status", methods=["POST"])
def update_status():
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

# Validation and Security Functions
def is_valid_integer(val):
    try:
        return int(val)
    except (TypeError, ValueError):
        return None
