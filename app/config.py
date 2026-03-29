import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'fallback-key')

    # Database
    DB_HOST     = os.getenv('DB_HOST', 'localhost')
    DB_PORT     = int(os.getenv('DB_PORT', 3306))
    DB_USER     = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_NAME     = os.getenv('DB_NAME', 'ai_learning_platform')

    # Session Security
    SESSION_COOKIE_HTTPONLY  = True
    SESSION_COOKIE_SAMESITE  = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)

    # Security Headers
    WTF_CSRF_ENABLED = True