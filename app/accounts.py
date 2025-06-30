import mysql.connector
import os
from flask import Flask, Blueprint, current_app, request, session, redirect, url_for
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

bp = Blueprint('accounts', __name__)

def get_db_connection():
    cfg = current_app.config
    return mysql.connector.connect(
        host=cfg['MYSQL_HOST'],
        user=cfg['MYSQL_USER'],
        password=cfg['MYSQL_PASSWORD'],
        database=cfg['MYSQL_DB'],
    )



# POST routes =============================================    
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

            # Check if username or email already exists
            check_query = "SELECT * FROM users WHERE username = %s OR email = %s"
            cursor.execute(check_query, (username, email))
            if cursor.fetchone():
                return "Username or email already exists", 400
            else:
                # Insert new user with prepared statement
                insert_query = """INSERT INTO users (username, email, pwd) VALUES (%s, %s, %s)"""
                cursor.execute(insert_query, (username, email, password))
                conn.commit()
                
            cursor.close()
            conn.close()
            return "Registration Success"
        except Exception as e:
            return f'MySQL connection error: {str(e)}'

