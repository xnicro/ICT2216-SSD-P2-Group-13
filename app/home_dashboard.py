import mysql.connector
import os
from flask import (
    Blueprint, current_app, request, session, jsonify
)
import datetime

CATEGORY_ICONS = {
    "Fires": "fa-solid fa-fire category-fires",
    "Faulty Facilities/Equipment": "fa-solid fa-screwdriver-wrench category-faulty",
    "Vandalism": "fa-solid fa-spray-can category-vandalism",
    "Suspicious Activity": "fa-solid fa-user-secret category-suspicious",
    "Others": "fa-solid fa-question-circle category-others"
}

def get_db_connection():
    cfg = current_app.config
    return mysql.connector.connect(
        host=cfg['MYSQL_HOST'],
        user=cfg['MYSQL_USER'],
        password=cfg['MYSQL_PASSWORD'],
        database=cfg['MYSQL_DB'],
    )

def get_report_by_id(report_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
        SELECT r.report_id, s.name AS status_name, r.category_name, r.is_anonymous, r.title, r.description, r.created_at 
            FROM reports r
            JOIN status s ON r.status_id = s.status_id
            WHERE r.report_id = %s
        """
        cursor.execute(query, (report_id,))
        report = cursor.fetchone()
        # Convert string to datetime object
        if report and isinstance(report['created_at'], str):
            report['created_at'] = datetime.strptime(report['created_at'], "%Y-%m-%d %H:%M:%S")
        
        report['category_icon'] = CATEGORY_ICONS.get(report['category_name'], "fa-solid fa-tag")
        
        return report
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

# Validation and Security Functions
def is_valid_integer(val):
    try:
        return int(val)
    except (TypeError, ValueError):
        return None
