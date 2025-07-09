import mysql.connector
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import datetime
from flask import Flask, Blueprint, abort, current_app, jsonify, render_template, request, session, redirect, url_for, \
    flash
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from flask_wtf.csrf import validate_csrf
from wtforms.validators import ValidationError
from extensions import limiter
from flask_limiter.errors import RateLimitExceeded
from access_control import login_required, permission_required, ROLE_REDIRECT_MAP
import re

# Import logging functions
from logging_config import log_security_event, log_application_event, log_database_event

bp = Blueprint('accounts', __name__)

# Create an Argon2 hasher instance (customizable parameters)
ph = PasswordHasher(
    time_cost=3,  # number of iterations (default: 2)
    memory_cost=65536,  # memory usage in kibibytes (64 MB)
    parallelism=4,  # number of threads
    hash_len=32,  # length of the hash
    salt_len=16  # length of random salt
)


def get_db_connection():
    cfg = current_app.config
    try:
        conn = mysql.connector.connect(
            host=cfg['MYSQL_HOST'],
            user=cfg['MYSQL_USER'],
            password=cfg['MYSQL_PASSWORD'],
            database=cfg['MYSQL_DB'],
        )
        return conn
    except Exception as e:
        log_database_event("connection_failed", details={"error": str(e), "source": "accounts"})
        raise


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

    validation_errors = []

    if not re.fullmatch(r'^[a-zA-Z0-9_.-]{3,20}$', username):
        validation_errors.append("Username must be 3–20 characters, only letters, numbers, _, -, or .")
        flash("Username must be 3–20 characters, only letters, numbers, _, -, or .", "error")

    if not re.fullmatch(r"^[^@]+@[^@]+\.[^@]+$", email):
        validation_errors.append("Invalid email format")
        flash("Invalid email format", "error")

    if len(password) < 8 or not re.search(r'[A-Z]', password) or not re.search(r'[0-9]', password):
        validation_errors.append("Password does not meet requirements")
        flash("Password must be at least 8 characters, include uppercase and a number.", "error")

    if password != confirm_password:
        validation_errors.append("Passwords do not match")
        flash("Passwords do not match", "error")

    # Log validation attempts
    if validation_errors:
        log_security_event("registration_validation_failed",
                           details={
                               "username": username,
                               "email": email,
                               "errors": validation_errors
                           },
                           request=request)
        return False

    return True


def validate_login_fields():
    username = request.form['username'].strip()
    password = request.form['password']

    validation_errors = []

    if not username or not password:
        validation_errors.append("Username and password are required")
        flash("Username and password are required.", "error")

    if len(username) > 20:
        validation_errors.append("Username too long")
        flash("Username too long", "error")

    if len(password) > 128:
        validation_errors.append("Password too long")
        flash("Password too long", "error")

    # Log validation attempts
    if validation_errors:
        log_security_event("login_validation_failed",
                           details={
                               "username": username,
                               "errors": validation_errors
                           },
                           request=request)
        return False

    return True


# GET routes =============================================
def get_all_users():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        query = """
        SELECT user_id, username, email, role
        FROM users 
        ORDER BY user_id
        """
        cursor.execute(query)
        users = cursor.fetchall()

        log_database_event("users_list_retrieved",
                           table="users",
                           details={"count": len(users), "requested_by": session.get('user_id')})

        return users
    except Exception as e:
        log_database_event("users_list_failed",
                           table="users",
                           details={"error": str(e), "requested_by": session.get('user_id')})
        raise
    finally:
        cursor.close()
        conn.close()


# POST routes =============================================
@bp.route("/register", methods=["POST"])
@limiter.limit("5 per minute")
def register_user():
    log_security_event("registration_attempt", request=request)

    if 'user_id' in session:
        log_security_event("registration_attempt_while_logged_in",
                           user_id=session.get('user_id'),
                           request=request)
        role = session.get('role')
        default_route = ROLE_REDIRECT_MAP.get(role, 'profile')
        flash("You are already logged in.", "info")
        return redirect(url_for(default_route))

    csrf_token = request.form.get("csrf_token")
    try:
        validate_csrf(csrf_token)
    except ValidationError:
        log_security_event("registration_csrf_validation_failed", request=request)
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

        # Check for existing user
        check_query = "SELECT * FROM users WHERE username = %s OR email = %s"
        cursor.execute(check_query, (username, email))
        existing_user = cursor.fetchone()

        if existing_user:
            log_security_event("registration_duplicate_user",
                               details={
                                   "attempted_username": username,
                                   "attempted_email": email
                               },
                               request=request)
            flash("Username or email already exists", "error")
            return redirect(url_for('register'))

        # Hash password and create user
        hashed = ph.hash(password)
        insert_query = """INSERT INTO users (username, email, pwd) VALUES (%s, %s, %s)"""
        cursor.execute(insert_query, (username, email, hashed))
        conn.commit()

        # Get the new user ID
        new_user_id = cursor.lastrowid

        # Log successful registration
        log_security_event("registration_successful",
                           user_id=new_user_id,
                           details={
                               "username": username,
                               "email": email
                           },
                           request=request)

        log_database_event("user_created",
                           table="users",
                           user_id=new_user_id,
                           details={
                               "username": username,
                               "email": email
                           })

        flash("Registration successful! Please login.", "success")
        return redirect(url_for('login'))

    except Exception as e:
        log_security_event("registration_error",
                           details={
                               "username": username,
                               "email": email,
                               "error": str(e)
                           },
                           request=request)
        flash(f'Registration error: {str(e)}', "error")
        return redirect(url_for('register'))
    finally:
        cursor.close()
        conn.close()

def generate_otp():
    otp = random.randint(100000, 999999)
    return otp

# Function to send OTP via email using smtplib
def send_otp_email(email, otp):
    sender_email = "sitsecure.notifications@gmail.com"
    sender_password = "wurhnkuxldbfnokf"
    smtp_server = "smtp.gmail.com"
    smtp_port = 587  # For TLS, change if using another provider

    # Create the message
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = email
    message["Subject"] = "Your OTP Code"
    
    body = f"Your one-time password is: {otp}. It will expire in 1 minutes."
    message.attach(MIMEText(body, "plain"))

    try:
        # Establish a connection to the SMTP server
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Secure connection using TLS
        server.login(sender_email, sender_password)  # Log in to the email account
        server.sendmail(sender_email, email, message.as_string())  # Send email
        server.close()
        print("Email sent successfully!")  # For debugging
    except Exception as e:
        print(f"Error sending email: {e}")  # For debugging

@bp.route("/login", methods=["POST"])
@limiter.limit("5 per minute")
def login_user():
    username = request.form.get('username', '').strip()

    log_security_event("login_attempt",
                       details={"username": username},
                       request=request)

    if 'user_id' in session:
        log_security_event("login_attempt_while_logged_in",
                           user_id=session.get('user_id'),
                           details={"attempted_username": username},
                           request=request)
        role = session.get('role')
        default_route = ROLE_REDIRECT_MAP.get(role, 'profile')
        flash("You are already logged in.", "info")
        return redirect(url_for(default_route))

    # Check if CSRF token matches
    csrf_token = request.form.get("csrf_token")
    try:
        validate_csrf(csrf_token)
    except ValidationError:
        log_security_event("login_csrf_validation_failed",
                           details={"username": username},
                           request=request)
        flash("Invalid or missing CSRF token", "error")
        return redirect(url_for('login'))

    if not validate_login_fields():
        return redirect(url_for('login'))

    if request.method == 'POST':
        password = request.form['password']

        # Basic validation
        if not username:
            log_security_event("login_empty_username", request=request)
            flash("Username cannot be empty", "error")
            return redirect(url_for('login'))
        if not password:
            log_security_event("login_empty_password",
                               details={"username": username},
                               request=request)
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

            if not verify_user:  # if no such user
                log_security_event("login_user_not_found",
                                   details={"username": username},
                                   request=request)
                flash("Invalid username or password", "error")
                return redirect(url_for('login'))

            try:  # Verify password
                ph.verify(verify_user['pwd'], password)

                # Password is correct, set up session
                session.clear()
                session.permanent = True

                session['user_id'] = verify_user['user_id']
                session['username'] = verify_user['username']
                session['email'] = verify_user['email']
                session['role'] = verify_user['role']
                session['verified'] = verify_user.get('verified', 0)

                # Log successful login
                log_security_event("login_successful",
                                   user_id=verify_user['user_id'],
                                   details={
                                       "username": username,
                                       "role": verify_user['role']
                                   },
                                   request=request)

                log_application_event("user_session_created",
                                      user_id=verify_user['user_id'],
                                      details={
                                          "username": username,
                                          "role": verify_user['role']
                                      })

                role = verify_user['role']
                default_route = ROLE_REDIRECT_MAP.get(role, 'profile')
                
                # Generate OTP and store it in the session
                otp = generate_otp()
                session['otp'] = otp
                session['otp_expiry'] = (datetime.datetime.now() + datetime.timedelta(minutes=1)).timestamp()
                
                 # Send OTP to user's email
                send_otp_email(verify_user['email'], otp)

                return redirect(url_for('accounts.verify_otp'))
                
                #return redirect(url_for(default_route))

            except VerifyMismatchError:
                log_security_event("login_wrong_password",
                                   details={
                                       "username": username,
                                       "user_id": verify_user['user_id']
                                   },
                                   request=request)
                flash("Invalid username or password", "error")
                return redirect(url_for('login'))

        except Exception as e:
            log_security_event("login_error",
                               details={
                                   "username": username,
                                   "error": str(e)
                               },
                               request=request)
            flash(f'Login error: {str(e)}', "error")
            return redirect(url_for('login'))

# OTP Verification Route
@bp.route("/verify_otp", methods=["GET", "POST"])
@login_required
def verify_otp():
    if request.method == "POST":
        entered_otp = request.form['otp']
        
        # Check if OTP is valid and not expired
        if 'otp' not in session or 'otp_expiry' not in session:
            flash("Session expired, please log in again.", "error")
            session.clear()
            return redirect(url_for('login'))

        if datetime.datetime.now().timestamp() > session['otp_expiry']:
            flash("OTP expired, please request a new one.", "error")
            session.pop('otp', None)
            session.pop('otp_expiry', None)
            session.clear()
            return redirect(url_for('login'))
        
        if not entered_otp.isdigit():
            flash("Invalid OTP format. Please enter only numerical values", "error")
            return redirect(url_for('accounts.verify_otp'))

        if int(entered_otp) == session['otp']:
            session['verified'] = True
            session.pop('otp', None)
            session.pop('otp_expiry', None)
            flash("Login successful!", "success")
            role = session.get('role')
            default_route = ROLE_REDIRECT_MAP.get(role, 'profile')
            return redirect(url_for(default_route))
        else:
            flash("Invalid OTP, please try again.", "error")
            return redirect(url_for('accounts.verify_otp'))

    return render_template('verify_otp.html')

@bp.route("/logout")
def logout():
    user_id = session.get('user_id')
    username = session.get('username')

    log_security_event("logout_attempt",
                       user_id=user_id,
                       details={"username": username},
                       request=request)

    # Logout user and clear session
    session.clear()

    log_security_event("logout_successful",
                       user_id=user_id,
                       details={"username": username},
                       request=request)

    log_application_event("user_session_ended",
                          user_id=user_id,
                          details={"username": username})

    flash("You have been logged out successfully", "info")
    return redirect(url_for('login'))


@bp.route("/update_role", methods=["POST"])
@login_required
@permission_required("manage_roles")
def update_role():
    admin_user_id = session.get('user_id')
    admin_username = session.get('username')

    log_security_event("role_update_attempt",
                       user_id=admin_user_id,
                       details={"admin_username": admin_username},
                       request=request)

    # Check if CSRF Matches
    csrf_token = request.headers.get("X-CSRFToken")
    try:
        validate_csrf(csrf_token)
    except ValidationError:
        log_security_event("role_update_csrf_failed",
                           user_id=admin_user_id,
                           request=request)
        return jsonify(success=False, error="Invalid or missing CSRF token"), 400

    data = request.get_json()

    user_id = is_valid_integer(data.get("user_id"))
    user_role = data.get("role")

    if not user_id:
        log_security_event("role_update_invalid_input",
                           user_id=admin_user_id,
                           details={"invalid_user_id": data.get("user_id")},
                           request=request)
        current_app.logger.warning("Invalid or missing user id")
        return jsonify(success=False, error="Invalid input."), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get current user info for logging
        cursor.execute("SELECT username, role FROM users WHERE user_id = %s", (user_id,))
        target_user = cursor.fetchone()

        if not target_user:
            log_security_event("role_update_user_not_found",
                               user_id=admin_user_id,
                               details={"target_user_id": user_id},
                               request=request)
            return jsonify(success=False, error="User not found"), 404

        # Update the role
        cursor.execute("""
            UPDATE users
            SET role = %s
            WHERE user_id = %s
        """, (user_role, user_id))
        conn.commit()

        # Log successful role update
        log_security_event("role_update_successful",
                           user_id=admin_user_id,
                           details={
                               "admin_username": admin_username,
                               "target_user_id": user_id,
                               "target_username": target_user['username'],
                               "old_role": target_user['role'],
                               "new_role": user_role
                           },
                           request=request)

        log_database_event("user_role_updated",
                           table="users",
                           user_id=user_id,
                           details={
                               "updated_by": admin_user_id,
                               "old_role": target_user['role'],
                               "new_role": user_role
                           })

        print("Update successful")
        return jsonify(success=True)

    except Exception as e:
        log_security_event("role_update_error",
                           user_id=admin_user_id,
                           details={
                               "target_user_id": user_id,
                               "intended_role": user_role,
                               "error": str(e)
                           },
                           request=request)
        print("Update failed:", e)
        return jsonify(success=False), 500
    finally:
        cursor.close()
        conn.close()


@bp.errorhandler(RateLimitExceeded)
def ratelimit_handler(e):
    retry_after = int(e.description.split(" ")[-1]) if "second" in str(e.description) else 60

    log_security_event("rate_limit_exceeded",
                       details={
                           "limit_type": "login_attempts",
                           "retry_after": retry_after,
                           "description": str(e.description)
                       },
                       request=request)

    flash("Too many login attempts. Please try again in a few minutes.", "error")
    return render_template('1_login.html', rate_limited=True, retry_after=retry_after), 429