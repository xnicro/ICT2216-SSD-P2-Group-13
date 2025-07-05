import mysql.connector
import os
from flask import Flask, Blueprint, abort, current_app, jsonify, render_template, request, session, redirect, url_for, flash
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from flask_wtf.csrf import validate_csrf
from wtforms.validators import ValidationError
from extensions import limiter
from flask_limiter.errors import RateLimitExceeded
from access_control import login_required, permission_required, ROLE_REDIRECT_MAP
import re

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
# Validation and Security Functions ======================== 
def is_valid_integer(val):
    try:
        return int(val)
    except (TypeError, ValueError):
        return None
    
def validate_registration_fields():
    username = request.form['username'].strip()
    email = request.form['email'].strip()
    password = request.form['password']
    confirm_password = request.form['confirm_password']

    if not re.fullmatch(r'^[a-zA-Z0-9_.-]{3,20}$', username):
        flash("Username must be 3–20 characters, only letters, numbers, _, -, or .", "error")
        return False

    if not re.fullmatch(r"^[^@]+@[^@]+\.[^@]+$", email):
        flash("Invalid email format", "error")
        return False

    if len(password) < 8 or not re.search(r'[A-Z]', password) or not re.search(r'[0-9]', password):
        flash("Password must be at least 8 characters, include uppercase and a number.", "error")
        return False

    if password != confirm_password:
        flash("Passwords do not match", "error")
        return False

    return True


def validate_login_fields():
    username = request.form['username'].strip()
    password = request.form['password']

    if not username or not password:
        flash("Username and password are required.", "error")
        return False
    if len(username) > 20:
        flash("Username too long", "error")
        return False
    if len(password) > 128:
        flash("Password too long", "error")
        return False
    return True

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
@limiter.limit("5 per minute")
def register_user():
    csrf_token = request.form.get("csrf_token")
    try:
        validate_csrf(csrf_token)
    except ValidationError:
        flash("Invalid or missing CSRF token", "error")
        return redirect(url_for('register'))

    # Call the central validation function
    if not validate_registration_fields():
        return redirect(url_for('register'))

    # Proceed with sanitized inputs
    username = request.form['username'].strip()
    email = request.form['email'].strip()
    password = request.form['password']

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        check_query = "SELECT * FROM users WHERE username = %s OR email = %s"
        cursor.execute(check_query, (username, email))
        if cursor.fetchone():
            flash("Username or email already exists", "error")
            return redirect(url_for('register'))

        hashed = ph.hash(password)
        insert_query = """INSERT INTO users (username, email, pwd) VALUES (%s, %s, %s)"""
        cursor.execute(insert_query, (username, email, hashed))
        conn.commit()

        flash("Registration successful! Please login.", "success")
        return redirect(url_for('login'))

    except Exception as e:
        flash(f'Registration error: {str(e)}', "error")
        return redirect(url_for('register'))
    finally:
        cursor.close()
        conn.close()

        
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
    
    if not validate_login_fields():
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
                default_route = ROLE_REDIRECT_MAP.get(role, 'profile')  # 'profile' is fallback
                return redirect(url_for(default_route))
            
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
@login_required
@permission_required("manage_roles")
def update_role():
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

