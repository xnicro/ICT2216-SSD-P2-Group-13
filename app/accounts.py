import mysql.connector
import os
from flask import Flask, Blueprint, abort, current_app, jsonify, render_template, request, session, redirect, url_for, flash
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from flask_wtf.csrf import validate_csrf
from wtforms.validators import ValidationError
from extensions import limiter
from flask_limiter.errors import RateLimitExceeded

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
# Validation and Security Functions
def is_valid_integer(val):
    try:
        return int(val)
    except (TypeError, ValueError):
        return None
    
# GET routes =============================================   
def get_all_users():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
        SELECT user_id, username, email, role
        FROM users 
        ORDER BY user_id
        """
        cursor.execute(query)
        users = cursor.fetchall()
        return users
    finally:
        cursor.close()
        conn.close()

# POST routes =============================================    
@bp.route("/register", methods=["POST"])
@limiter.limit("5 per 2 minutes")
def register_user():
    # Check if CSRF token matches
    csrf_token = request.form.get("csrf_token")
    try:
        validate_csrf(csrf_token)
    except ValidationError:
        flash("Invalid or missing CSRF token", "error")
        return redirect(url_for('register'))
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Basic validation
        if len(username) < 3:
            flash("Username must be at least 3 characters", "error")
            return redirect(url_for('register'))
        if not username.isalnum():  # Only allow letters and numbers
            flash("Username can only contain letters and numbers", "error")
            return redirect(url_for('register'))
        if not email:
            flash("Email cannot be empty", "error")
            return redirect(url_for('register'))
        if not password:
            flash("Password cannot be empty", "error")
            return redirect(url_for('register'))
        if not confirm_password:
            flash("Confirm Password cannot be empty", "error")
            return redirect(url_for('register'))
        if password != confirm_password:
            flash("Passwords don't match", "error")
            return redirect(url_for('register'))
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Check if username or email already exists
            check_query = "SELECT * FROM users WHERE username = %s OR email = %s"
            cursor.execute(check_query, (username, email))
            if cursor.fetchone():
                flash("Username or email already exists", "error")
                return redirect(url_for('register'))
            else:
                # Insert new user with prepared statement
                insert_query = """INSERT INTO users (username, email, pwd) VALUES (%s, %s, %s)"""
                hashed = ph.hash(password) #hash password
                cursor.execute(insert_query, (username, email, hashed))
                conn.commit()
                
            cursor.close()
            conn.close()
            flash("Registration successful! Please login.", "success")
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Registration error: {str(e)}', "error")
            return redirect(url_for('register'))
        
        
@bp.route("/login", methods=["POST"])
@limiter.limit("5 per minute")
def login_user():
    # Check if CSRF token matches
    csrf_token = request.form.get("csrf_token")
    try:
        validate_csrf(csrf_token)
    except ValidationError:
        flash("Invalid or missing CSRF token", "error")
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

         # Basic validation
        if not username:
            flash("Username cannot be empty", "error")
            return redirect(url_for('login'))
        if not password:
            flash("Password cannot be empty", "error")
            return redirect(url_for('login'))
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            # Get user by username
            query = "SELECT * FROM users WHERE username = %s"
            cursor.execute(query, (username,))
            verify_user = cursor.fetchone()
            cursor.close()
            conn.close()

            if not verify_user: #if no such user
                flash("Invalid username or password", "error")
                return redirect(url_for('login'))
            
            try: # Verify password
                ph.verify(verify_user['pwd'], password)
                
                session.clear()
                session.permanent = True
                
                # Password is correct, set up session
                session['user_id'] = verify_user['user_id']
                session['username'] = verify_user['username']
                session['email'] = verify_user['email']
                session['role'] = verify_user['role']
                session['verified'] = verify_user.get('verified', 0)  # Default to 0 if column doesn't exist
                
                role = verify_user['role']
                if role == 'admin':
                    return redirect(url_for('admin'))  
                elif role == 'superadmin':
                    return redirect(url_for('role'))
                else:
                    return redirect(url_for('profile'))  # Regular user

            
            except VerifyMismatchError:
                flash("Invalid username or password", "error")
                return redirect(url_for('login'))
            
        except Exception as e:
            flash(f'Login error: {str(e)}', "error")
            return redirect(url_for('login'))

@bp.route("/logout")
def logout():
    # Logout user and clear session
    session.clear()
    flash("You have been logged out successfully", "info")
    return redirect(url_for('login'))

@bp.route("/update_role", methods=["POST"])
def update_role():
    if session.get("role") != "superadmin":
        abort(403)

    # Check if CSRF Matches
    csrf_token = request.headers.get("X-CSRFToken")
    try:
        validate_csrf(csrf_token)
    except ValidationError:
        return jsonify(success=False, error="Invalid or missing CSRF token"), 400
    
    data = request.get_json()

    user_id = is_valid_integer(data.get("user_id"))
    user_role = data.get("role")

    if not user_id:
        current_app.logger.warning("Invalid or missing user id")
        return jsonify(success=False, error="Invalid input."), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users
            SET role = %s
            WHERE user_id = %s
        """, (user_role, user_id))
        conn.commit()
        print("Update successful")
        return jsonify(success=True)
    except Exception as e:
        print("Update failed:", e)
        return jsonify(success=False), 500
    finally:
        cursor.close()
        conn.close()

@bp.errorhandler(RateLimitExceeded)
def ratelimit_handler(e):
    retry_after = int(e.description.split(" ")[-1]) if "second" in str(e.description) else 60 
    flash("Too many login attempts. Please try again in a few minutes.", "error")
    return render_template('1_login.html', rate_limited=True, retry_after=retry_after), 429


# Success routes ====================================================
@bp.route('/register_success')
def register_success():
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

