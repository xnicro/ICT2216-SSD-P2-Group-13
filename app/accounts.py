import mysql.connector
import os
from flask import (
    Blueprint, current_app, request, session, jsonify
)

bp = Blueprint('register_user', __name__)

def get_db_connection():
    cfg = current_app.config
    return mysql.connector.connect(
        host=cfg['MYSQL_HOST'],
        user=cfg['MYSQL_USER'],
        password=cfg['MYSQL_PASSWORD'],
        database=cfg['MYSQL_DB'],
    )

def insert_user():
    try:
        conn = get_db_connection()
        
        cursor.execute('SELECT * FROM test;')
        conn.commit()
        conn.close()
        return redirect(url_for('registration_success'))
    except sqlite3.IntegrityError:
        return "Username or email already exists!"