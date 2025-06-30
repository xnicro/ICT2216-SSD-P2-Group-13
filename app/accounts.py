import mysql.connector
import os
from flask import Flask, Blueprint, current_app, request, session, redirect, url_for

bp = Blueprint('register_user', __name__)

def get_db_connection():
    cfg = current_app.config
    return mysql.connector.connect(
        host=cfg['MYSQL_HOST'],
        user=cfg['MYSQL_USER'],
        password=cfg['MYSQL_PASSWORD'],
        database=cfg['MYSQL_DB'],
    )

    
@bp.route("/register", methods=["POST"])
def register_user():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Basic validation
        if password != confirm_password:
            return "Passwords don't match", 400
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM test;')
            conn.commit()

            # Check if username or email already exists
            check_query = "SELECT * FROM users WHERE username = %s"
            cursor.execute(check_query, (username))
            if cursor.fetchone():
                return "Username or email already exists", 400
            else:
                # Insert new user with prepared statement
                insert_query = """INSERT INTO users (username, email, pwd) VALUES (%s, %s, %s)"""
                cursor.execute(insert_query, (username, email, password))
                conn.commit()
            cursor.close()
            conn.close()
            return redirect(url_for('success'))
        except Exception as e:
            return f'MySQL connection error: {str(e)}'


@bp.route('/success')
def success():
    return "Registration successful!"