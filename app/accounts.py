import mysql.connector
import os
from flask import Flask, Blueprint, current_app, request, session, redirect, url_for
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

bp = Blueprint('accounts', __name__)

# Create an Argon2 hasher instance (customizable parameters)
ph = PasswordHasher(
    time_cost=3,       # number of iterations (default: 2)
    memory_cost=65536, # memory usage in kibibytes (64 MB)
    parallelism=4,     # number of threads
    hash_len=32,       # length of the hash
    salt_len=16        # length of random salt
)

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
        if len(username) < 3:
            return "Username must be at least 3 characters", 400
        if not username.isalnum():  # Only allow letters and numbers
            return "Username can only contain letters and numbers", 400
        if not email:
            return "Email cannot be empty", 400
        if not password:
            return "Password cannot be empty", 400
        if not confirm_password:
            return "Confirm Password cannot be empty", 400
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
                hashed = ph.hash(password)
                cursor.execute(insert_query, (username, email, hashed))
                conn.commit()
                
            cursor.close()
            conn.close()
            return redirect(url_for('accounts.success'))
        except Exception as e:
            return f'MySQL connection error: {str(e)}'

@bp.route('/success')
def success():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Registration Successful</title>
        <h1>Registration Successful</h1>
        <style>
            body {
                font-family: Arial, sans-serif;
                text-align: center;
                padding: 50px;
            }
            .back-button {
                padding: 10px 20px;
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 16px;
                text-decoration: none;
                display: inline-block;
            }
            .back-button:hover {
                background-color: #45a049;
            }
        </style>
    </head>
    <body>
        <a href="/" class="back-button">Go Back to Home</a>
    </body>
    </html>
    """
