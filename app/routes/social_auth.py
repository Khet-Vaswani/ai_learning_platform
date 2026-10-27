# ============================================================
# social_auth.py — Google, GitHub, LinkedIn OAuth
# ============================================================

from flask import (Blueprint, redirect, url_for,
                   session, request, jsonify)
from app.utils.db import execute_query
import os, requests, json, secrets

social_bp = Blueprint('social', __name__)

# ── Google OAuth ──────────────────────────────────────────
GOOGLE_AUTH_URL    = 'https://accounts.google.com/o/oauth2/auth'
GOOGLE_TOKEN_URL   = 'https://oauth2.googleapis.com/token'
GOOGLE_USERINFO_URL= 'https://www.googleapis.com/oauth2/v2/userinfo'

# ── GitHub OAuth ──────────────────────────────────────────
GITHUB_AUTH_URL    = 'https://github.com/login/oauth/authorize'
GITHUB_TOKEN_URL   = 'https://github.com/login/oauth/access_token'
GITHUB_USERINFO_URL= 'https://api.github.com/user'
GITHUB_EMAIL_URL   = 'https://api.github.com/user/emails'

# ── LinkedIn OAuth ────────────────────────────────────────
LINKEDIN_AUTH_URL    = 'https://www.linkedin.com/oauth/v2/authorization'
LINKEDIN_TOKEN_URL   = 'https://www.linkedin.com/oauth/v2/accessToken'
LINKEDIN_USERINFO_URL= 'https://api.linkedin.com/v2/userinfo'


def _new_state(provider):
    """Random OAuth state stored in the session (prevents login CSRF)."""
    state = secrets.token_urlsafe(24)
    session[f'oauth_state_{provider}'] = state
    return state


def _valid_state(provider):
    expected = session.pop(f'oauth_state_{provider}', None)
    received = request.args.get('state', '')
    return bool(expected) and secrets.compare_digest(expected, received)


def login_or_register_social(email, full_name, provider):
    """
    Check if user exists → login
    If not → register automatically
    """
    if not email:
        return None
    email = email.strip().lower()   # stored emails are lowercase

    # Check existing user
    user = execute_query(
        "SELECT * FROM users WHERE email=%s",
        (email,), fetch=True
    )

    if user:
        u = user[0]
        session['user_id']         = u['id']
        session['user_name']       = u['full_name']
        session['user_email']      = u['email']
        session['user_role']       = u.get('role', 'student')
        session['onboarding_done'] = u.get('onboarding_done', 0)
        print(f"✅ {provider} login: {email}")
        return u

    # Register new user
    import bcrypt
    fake_pw = bcrypt.hashpw(
        os.urandom(24), bcrypt.gensalt()
    ).decode('utf-8')

    user_id = execute_query(
        """INSERT INTO users
           (full_name, email, password, role, onboarding_done)
           VALUES (%s,%s,%s,'student',0)""",
        (full_name, email, fake_pw)
    )
    if not user_id:
        return None

    session['user_id']         = user_id
    session['user_name']       = full_name
    session['user_email']      = email
    session['user_role']       = 'student'
    session['onboarding_done'] = 0

    print(f"✅ {provider} register: {email}")
    return {'id': user_id, 'onboarding_done': 0}


# ============================================================
# GOOGLE
# ============================================================
@social_bp.route('/auth/google')
def google_login():
    import urllib.parse
    params = {
        'client_id'    : os.getenv('GOOGLE_CLIENT_ID'),
        'redirect_uri' : url_for('social.google_callback',
                                  _external=True),
        'response_type': 'code',
        'scope'        : 'openid email profile',
        'access_type'  : 'offline',
        'state'        : _new_state('google')
    }
    url = GOOGLE_AUTH_URL + '?' + urllib.parse.urlencode(params)
    return redirect(url)


@social_bp.route('/auth/google/callback')
def google_callback():
    code = request.args.get('code')
    if not code or not _valid_state('google'):
        return redirect('/login?error=google_failed')

    try:
        # Exchange code for token
        token_res = requests.post(GOOGLE_TOKEN_URL, data={
            'code'         : code,
            'client_id'    : os.getenv('GOOGLE_CLIENT_ID'),
            'client_secret': os.getenv('GOOGLE_CLIENT_SECRET'),
            'redirect_uri' : url_for('social.google_callback',
                                      _external=True),
            'grant_type'   : 'authorization_code'
        })
        token_data = token_res.json()
        access_token = token_data.get('access_token')

        if not access_token:
            return redirect('/login?error=google_token_failed')

        # Get user info
        user_res = requests.get(
            GOOGLE_USERINFO_URL,
            headers={'Authorization': f'Bearer {access_token}'}
        )
        user_data  = user_res.json()
        email      = user_data.get('email', '') if user_data.get('verified_email') else ''
        full_name  = user_data.get('name', email.split('@')[0])

        user = login_or_register_social(email, full_name, 'Google')

        if not user:
            return redirect('/login?error=no_email')

        if session.get('onboarding_done'):
            return redirect('/dashboard')
        else:
            return redirect('/cognitive-test')

    except Exception as e:
        print(f"❌ Google OAuth error: {e}")
        return redirect('/login?error=google_error')


# ============================================================
# GITHUB
# ============================================================
@social_bp.route('/auth/github')
def github_login():
    import urllib.parse
    params = {
        'client_id'   : os.getenv('GITHUB_CLIENT_ID'),
        'redirect_uri': url_for('social.github_callback',
                                 _external=True),
        'scope'       : 'user:email',
        'state'       : _new_state('github')
    }
    url = GITHUB_AUTH_URL + '?' + urllib.parse.urlencode(params)
    return redirect(url)


@social_bp.route('/auth/github/callback')
def github_callback():
    code = request.args.get('code')
    if not code or not _valid_state('github'):
        return redirect('/login?error=github_failed')

    try:
        # Exchange code for token
        token_res = requests.post(
            GITHUB_TOKEN_URL,
            data={
                'client_id'    : os.getenv('GITHUB_CLIENT_ID'),
                'client_secret': os.getenv('GITHUB_CLIENT_SECRET'),
                'code'         : code,
                'redirect_uri' : url_for('social.github_callback',
                                          _external=True)
            },
            headers={'Accept': 'application/json'}
        )
        token_data   = token_res.json()
        access_token = token_data.get('access_token')

        if not access_token:
            return redirect('/login?error=github_token_failed')

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept'       : 'application/json'
        }

        # Get user info
        user_res  = requests.get(GITHUB_USERINFO_URL, headers=headers)
        user_data = user_res.json()
        full_name = user_data.get('name') or \
                    user_data.get('login', 'GitHub User')
        # Always use the emails endpoint: only a verified primary email
        # may be matched to an existing account
        email      = None
        emails_res = requests.get(GITHUB_EMAIL_URL, headers=headers)
        emails     = emails_res.json()
        for e in emails if isinstance(emails, list) else []:
            if e.get('primary') and e.get('verified'):
                email = e['email']
                break

        user = login_or_register_social(email, full_name, 'GitHub')

        if not user:
            return redirect('/login?error=no_email')

        if session.get('onboarding_done'):
            return redirect('/dashboard')
        else:
            return redirect('/cognitive-test')

    except Exception as e:
        print(f"❌ GitHub OAuth error: {e}")
        return redirect('/login?error=github_error')


# ============================================================
# LINKEDIN
# ============================================================
@social_bp.route('/auth/linkedin')
def linkedin_login():
    import urllib.parse
    params = {
        'response_type': 'code',
        'client_id'    : os.getenv('LINKEDIN_CLIENT_ID'),
        'redirect_uri' : url_for('social.linkedin_callback',
                                  _external=True),
        'scope'        : 'openid profile email',
        'state'        : _new_state('linkedin')
    }
    url = LINKEDIN_AUTH_URL + '?' + urllib.parse.urlencode(params)
    return redirect(url)


@social_bp.route('/auth/linkedin/callback')
def linkedin_callback():
    code = request.args.get('code')
    if not code or not _valid_state('linkedin'):
        return redirect('/login?error=linkedin_failed')

    try:
        # Exchange code for token
        token_res = requests.post(
            LINKEDIN_TOKEN_URL,
            data={
                'grant_type'  : 'authorization_code',
                'code'        : code,
                'redirect_uri': url_for('social.linkedin_callback',
                                         _external=True),
                'client_id'   : os.getenv('LINKEDIN_CLIENT_ID'),
                'client_secret': os.getenv('LINKEDIN_CLIENT_SECRET')
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        token_data   = token_res.json()
        access_token = token_data.get('access_token')

        if not access_token:
            return redirect('/login?error=linkedin_token_failed')

        # Get user info (OpenID Connect)
        user_res  = requests.get(
            LINKEDIN_USERINFO_URL,
            headers={'Authorization': f'Bearer {access_token}'}
        )
        user_data = user_res.json()
        email     = user_data.get('email', '') if user_data.get('email_verified') else ''
        full_name = user_data.get('name', '') or \
                    (user_data.get('given_name', '') + ' ' +
                     user_data.get('family_name', '')).strip()

        user = login_or_register_social(email, full_name, 'LinkedIn')

        if not user:
            return redirect('/login?error=no_email')

        if session.get('onboarding_done'):
            return redirect('/dashboard')
        else:
            return redirect('/cognitive-test')

    except Exception as e:
        print(f"❌ LinkedIn OAuth error: {e}")
        return redirect('/login?error=linkedin_error')