# I MUST ADD ACCESS CONTROL SUCH AS SESSION.GET(ADMIN) OR SMT FOR ALL FUNCTIONS IN FUTURE
import mysql.connector
import os
from flask import (
    Blueprint, current_app, request, session, jsonify
)
import datetime


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
        return report
    finally:
        cursor.close()
        conn.close()

# Validation and Security Functions
def is_valid_integer(val):
    try:
        return int(val)
    except (TypeError, ValueError):
        return None
