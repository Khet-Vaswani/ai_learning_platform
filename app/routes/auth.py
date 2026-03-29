# ============================================================
# auth.py — Authentication Routes
# ============================================================

from flask import (Blueprint, render_template, request,
                   redirect, url_for, session, flash)
from app.utils.db import execute_query
from app.utils.auth_helpers import (hash_password,
                                     verify_password,
                                     check_rate_limit)
import re

auth = Blueprint('auth', __name__)


# ============================================================
# LOGIN
# ============================================================
@auth.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':

        # Rate limit
        ip = request.remote_addr
        if not check_rate_limit(ip):
            return render_template('login.html',
                error='Too many attempts. Wait 5 minutes.')

        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        # Validation
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
                      role, onboarding_done
               FROM users WHERE email=%s""",
            (email,), fetch=True
        )

        if not users:
            return render_template('login.html',
                error='Email not found.')

        user = users[0]

        if not verify_password(password, user['password']):
            return render_template('login.html',
                error='Incorrect password.')

        session.permanent          = True
        session['user_id']         = user['id']
        session['user_name']       = user['full_name']
        session['user_email']      = user['email']
        session['user_role']       = user['role']
        session['onboarding_done'] = user['onboarding_done']

        if user['role'] == 'admin':
            return redirect('/admin/dashboard')

        if not user['onboarding_done']:
            return redirect(url_for('cognitive.cognitive_test'))

        return redirect(url_for('dashboard.index'))

    return render_template('login.html')


# ============================================================
# REGISTER
# ============================================================
@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email     = request.form.get('email', '').strip().lower()
        password  = request.form.get('password', '')
        confirm   = request.form.get('confirm_password', '')

        # Validation
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
            """INSERT INTO users
               (full_name, email, password)
               VALUES (%s,%s,%s)""",
            (full_name, email, hashed_pw)
        )

        if user_id:
            flash('Account created! Please login.', 'success')
            return redirect(url_for('auth.login'))
        else:
            return render_template('register.html',
                error='Registration failed. Try again.')

    return render_template('register.html')


# ============================================================
# LOGOUT
# ============================================================
@auth.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'info')
    return redirect(url_for('auth.login'))