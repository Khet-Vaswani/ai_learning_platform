# ============================================================
# app/ai/__init__.py  ←  FINAL FIXED VERSION
# ============================================================
# Aapki dashboard.py mein blueprint ka naam "dashboard" hai
# isliye yahan bhi "dashboard" import kar rahe hain
# ============================================================

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

    # ── Security Headers ──────────────────────────────────
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options']        = 'SAMEORIGIN'
        response.headers['X-XSS-Protection']       = '1; mode=block'
        response.headers['Referrer-Policy']        = 'strict-origin'
        return response

    # ── Blueprints ────────────────────────────────────────
    from app.routes.auth        import auth
    from app.routes.cognitive   import cognitive_bp
    from app.routes.dashboard   import dashboard      # ← your file has "dashboard"
    from app.routes.youtube     import youtube_bp
    from app.routes.gemini      import gemini_bp
    from app.routes.recommend   import recommend_bp
    from app.routes.admin       import admin_bp
    from app.routes.social_auth import social_bp
    from app.routes.onboarding  import onboarding_bp

    app.register_blueprint(auth)
    app.register_blueprint(cognitive_bp)
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