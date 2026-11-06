# ============================================================
# app/ai/__init__.py  ←  FINAL FIXED VERSION
# ============================================================
# Aapki dashboard.py mein blueprint ka naam "dashboard" hai
# isliye yahan bhi "dashboard" import kar rahe hain
# ============================================================

import sys
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import os
from flask import Flask, redirect, url_for
from app.config import Config

BASE_DIR        = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
TEMPLATE_FOLDER = os.path.join(BASE_DIR, 'templates')
STATIC_FOLDER   = os.path.join(BASE_DIR, 'static')


def create_app():
    # Run database migrations on startup
    try:
        import sys
        import os
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        if base not in sys.path:
            sys.path.insert(0, base)
        import migrate_schema
        migrate_schema.run_migrations()
    except Exception as e:
        print(f"[ERROR] Failed to run auto-migrations: {e}")

    app = Flask(__name__,
        template_folder = TEMPLATE_FOLDER,
        static_folder   = STATIC_FOLDER
    )
    app.config.from_object(Config)

    # On Vercel the app sits behind a proxy: trust its X-Forwarded-* headers so
    # request.is_secure and url_for(_external=True) use https and the real host
    # (OAuth redirect URIs and password-reset links depend on this)
    if os.getenv('VERCEL'):
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    # ── Security Headers ──────────────────────────────────
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options']        = 'SAMEORIGIN'
        response.headers['X-XSS-Protection']       = '1; mode=block'
        response.headers['Referrer-Policy']        = 'strict-origin'
        return response

    # Password rule, shown on every form that sets a password (checked in auth_helpers)
    @app.context_processor
    def password_rule():
        from app.utils.auth_helpers import PASSWORD_RULE
        return {'password_rule': PASSWORD_RULE,
                'password_pattern': r'(?=.*\p{L})(?=.*\p{N})(?=.*[^\p{L}\p{N}\s]).{8,100}'}

    # ── Blueprints ────────────────────────────────────────
    from app.routes.auth        import auth
    from app.routes.dashboard   import dashboard      # ← your file has "dashboard"
    from app.routes.youtube     import youtube_bp
    from app.routes.gemini      import gemini_bp
    from app.routes.recommend   import recommend_bp
    from app.routes.admin       import admin_bp
    from app.routes.social_auth import social_bp
    from app.routes.onboarding  import onboarding_bp

    app.register_blueprint(auth)
    app.register_blueprint(dashboard)               # ← same name
    app.register_blueprint(youtube_bp)
    app.register_blueprint(gemini_bp)
    app.register_blueprint(recommend_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(social_bp)
    app.register_blueprint(onboarding_bp)

    # ── Root redirect ─────────────────────────────────────
    @app.route('/')
    def home():
        return redirect(url_for('auth.login'))

    return app