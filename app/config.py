import os
import secrets
from datetime import timedelta

from dotenv import load_dotenv

# Load .env before reading any setting (on Vercel the variables are already set)
load_dotenv()

# Set automatically by Vercel on every deployment
ON_VERCEL = bool(os.getenv('VERCEL'))


def _secret_key():
    key = os.getenv('SECRET_KEY')
    if key:
        return key
    if ON_VERCEL:
        # A built-in fallback would be public (it's in the code) and let anyone forge logins
        raise RuntimeError('SECRET_KEY is not set. Add it in Vercel: Settings → Environment Variables.')
    print('[WARN] SECRET_KEY is not set in .env; using a temporary key (you will be logged out on restart)')
    return secrets.token_hex(32)


class Config:
    SECRET_KEY = _secret_key()

    # Database
    DB_HOST     = os.getenv('DB_HOST', 'localhost')
    DB_PORT     = int(os.getenv('DB_PORT', 3306))
    DB_USER     = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_NAME     = os.getenv('DB_NAME', 'ai_learning_platform')

    # Session Security
    SESSION_COOKIE_HTTPONLY  = True
    SESSION_COOKIE_SAMESITE  = 'Lax'
    SESSION_COOKIE_SECURE    = ON_VERCEL          # HTTPS-only cookies on the live site
    PREFERRED_URL_SCHEME     = 'https' if ON_VERCEL else 'http'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)

    # Security Headers
    WTF_CSRF_ENABLED = True