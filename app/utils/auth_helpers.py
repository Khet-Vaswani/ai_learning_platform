from flask import session, redirect, url_for, request, jsonify
from functools import wraps
from app.utils.db import execute_query
import bcrypt
import time

# ── Password Functions ────────────────────────────────────
PASSWORD_RULE = 'Use at least 8 characters, with a letter, a number and a special character (like ! @ # $).'


def password_problem(password):
    """Why a new password isn't allowed, or None if it's fine."""
    if len(password) < 8:
        return 'Password must be at least 8 characters.'
    if len(password) > 100:
        return 'Password must be 100 characters or fewer.'
    if not any(c.isalpha() for c in password):
        return 'Password must contain at least one letter.'
    if not any(c.isdigit() for c in password):
        return 'Password must contain at least one number.'
    if not any(not c.isalnum() and not c.isspace() for c in password):
        return 'Password must contain at least one special character (like ! @ # $).'
    return None


def hash_password(password):
    return bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')


def verify_password(password, hashed):
    try:
        return bcrypt.checkpw(
            password.encode('utf-8'),
            hashed.encode('utf-8')
        )
    except Exception:
        return False


# ── Rate Limiter ──────────────────────────────────────────
_login_attempts = {}

def check_rate_limit(ip, max_attempts=5, window=300):
    now = time.time()
    if ip not in _login_attempts:
        _login_attempts[ip] = []

    _login_attempts[ip] = [
        t for t in _login_attempts[ip]
        if now - t < window
    ]

    if len(_login_attempts[ip]) >= max_attempts:
        return False

    _login_attempts[ip].append(now)
    return True


# ── Login Required ────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


# ── Admin Required ────────────────────────────────────────
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/admin/login')
        if session.get('user_role') != 'admin':
            return redirect('/admin/login')
        return f(*args, **kwargs)
    return decorated