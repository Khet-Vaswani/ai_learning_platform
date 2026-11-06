# ============================================================
# auth.py — Authentication Routes
# ============================================================

from flask import (Blueprint, render_template, request,
                   redirect, url_for, session, flash)
from app.utils.db import execute_query
from app.utils.auth_helpers import (hash_password,
                                     verify_password,
                                     check_rate_limit)
import os
import re

auth = Blueprint('auth', __name__)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        ip = request.remote_addr
        if not check_rate_limit(ip):
            return render_template('login.html',
                error='Too many attempts. Wait 5 minutes.')

        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            return render_template('login.html',
                error='All fields required.')
        if len(email) > 100 or len(password) > 100:
            return render_template('login.html',
                error='Invalid input.')
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            return render_template('login.html',
                error='Invalid email format.')

        users = execute_query(
            """SELECT id, full_name, email, password,
                      role, onboarding_done,
                      field_of_interest, skill_level
               FROM users WHERE email=%s""",
            (email,), fetch=True
        )

        # Same message for both cases, so the form can't be used to find out who has an account
        if not users or not verify_password(password, users[0]['password']):
            return render_template('login.html',
                error='Incorrect email or password.', email=email)

        user = users[0]

        session.permanent            = True
        session['user_id']           = user['id']
        session['user_name']         = user['full_name']
        session['user_email']        = user['email']
        session['user_role']         = user['role']
        session['onboarding_done']   = user['onboarding_done']
        session['field_of_interest'] = user.get('field_of_interest')
        session['skill_level']       = user.get('skill_level', 'Beginner')

        if user['role'] == 'admin':
            return redirect('/admin/dashboard')

        return redirect(url_for('dashboard.index'))

    return render_template('login.html')


@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email     = request.form.get('email', '').strip().lower()
        password  = request.form.get('password', '')
        confirm   = request.form.get('confirm_password', '')

        if not full_name or not email or not password:
            return render_template('register.html',
                error='All fields required.')
        if len(full_name) > 50:
            return render_template('register.html',
                error='Name too long.')
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            return render_template('register.html',
                error='Invalid email format.')
        if len(password) < 6:
            return render_template('register.html',
                error='Password must be at least 6 characters.')
        if password != confirm:
            return render_template('register.html',
                error='Passwords do not match.')

        existing = execute_query(
            "SELECT id FROM users WHERE email=%s",
            (email,), fetch=True
        )
        if existing:
            return render_template('register.html',
                error='Email already registered.')

        hashed_pw = hash_password(password)
        user_id   = execute_query(
            """INSERT INTO users (full_name, email, password)
               VALUES (%s, %s, %s)""",
            (full_name, email, hashed_pw)
        )

        if user_id:
            session.permanent            = True
            session['user_id']           = user_id
            session['user_name']         = full_name
            session['user_email']        = email
            session['user_role']         = 'student'
            session['onboarding_done']   = 0
            session['field_of_interest'] = None
            session['skill_level']       = 'Beginner'

            # New user → preferences page
            return redirect(url_for('onboarding.preferences'))
        else:
            return render_template('register.html',
                error='Registration failed. Try again.')

    return render_template('register.html')


@auth.route('/logout')
def logout():
    session.clear()
    flash("You've been logged out.", 'info')
    return redirect(url_for('auth.login'))


import secrets
from datetime import datetime, timedelta

@auth.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if 'user_id' in session:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        ip = request.remote_addr
        if not check_rate_limit(ip):
            return render_template('forgot_password.html',
                error='Too many reset attempts. Please wait 5 minutes.')

        email = request.form.get('email', '').strip().lower()

        if not email or not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            return render_template('forgot_password.html',
                error='Please provide a valid email address.')

        users = execute_query(
            "SELECT id, full_name FROM users WHERE email=%s",
            (email,), fetch=True
        )

        from app.utils.mailer import mail_configured, send_email

        # Same response whether or not the email exists (prevents account enumeration)
        generic_msg = ("If that email is registered, we've sent it a link to reset your password. "
                       "Check your inbox and spam folder." if mail_configured() else
                       'If that email is registered, password reset instructions have been generated.')

        if not users:
            return render_template('forgot_password.html', success=generic_msg)

        user = users[0]
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(minutes=30)

        # Invalidate existing unused tokens for this user
        execute_query(
            "UPDATE password_resets SET used=1 WHERE user_id=%s AND used=0",
            (user['id'],), fetch=False
        )

        # Insert new reset token
        execute_query(
            """INSERT INTO password_resets (user_id, token, expires_at)
               VALUES (%s, %s, %s)""",
            (user['id'], token, expires_at.strftime('%Y-%m-%d %H:%M:%S')),
            fetch=False
        )

        reset_link = url_for('auth.reset_password', token=token, _external=True)

        if mail_configured():
            send_email(
                email, 'Reset your LearnAI password',
                f"Hi {user['full_name']},\n\n"
                f"Use this link to choose a new password. It works once and expires in 30 minutes:\n\n"
                f"{reset_link}\n\n"
                f"If you didn't ask to reset your password, you can ignore this email.\n")
            show_link = False
        else:
            # No mail server configured: the link goes to the server console.
            # Showing it to whoever submitted the form would let anyone reset any
            # account; set SHOW_RESET_LINK=1 only for local demos.
            print(f"[PASSWORD RESET] {email}: {reset_link}")
            show_link = os.getenv('SHOW_RESET_LINK') == '1'

        return render_template('forgot_password.html',
            success=generic_msg,
            reset_link=reset_link if show_link else None)

    return render_template('forgot_password.html')


@auth.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if 'user_id' in session:
        return redirect(url_for('dashboard.index'))

    resets = execute_query(
        """SELECT r.id, r.user_id, r.expires_at, r.used, u.email
           FROM password_resets r
           JOIN users u ON r.user_id = u.id
           WHERE r.token=%s AND r.used=0""",
        (token,), fetch=True
    )

    if not resets:
        return render_template('reset_password.html',
            invalid=True, error='Invalid or expired password reset link.')

    reset_record = resets[0]
    expires_at = reset_record['expires_at']
    if isinstance(expires_at, str):
        expires_at = datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S')

    if datetime.now() > expires_at:
        execute_query("UPDATE password_resets SET used=1 WHERE id=%s", (reset_record['id'],), fetch=False)
        return render_template('reset_password.html',
            invalid=True, error='This password reset link has expired. Please request a new one.')

    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm_password', '')

        if not password or not confirm:
            return render_template('reset_password.html',
                token=token, error='All fields are required.')

        if len(password) < 6:
            return render_template('reset_password.html',
                token=token, error='Password must be at least 6 characters.')

        if password != confirm:
            return render_template('reset_password.html',
                token=token, error='Passwords do not match.')

        hashed_pw = hash_password(password)

        # Update user password
        execute_query(
            "UPDATE users SET password=%s WHERE id=%s",
            (hashed_pw, reset_record['user_id']), fetch=False
        )

        # Mark token as used
        execute_query(
            "UPDATE password_resets SET used=1 WHERE id=%s",
            (reset_record['id'],), fetch=False
        )

        flash('Password updated. Log in with your new password.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('reset_password.html', token=token)