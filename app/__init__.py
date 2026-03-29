from flask import Flask, redirect, url_for
from app.config import Config


def create_app():
    app = Flask(
        __name__,
        template_folder='../templates',
        static_folder='../static'
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
    from app.routes.cognitive   import cognitive_bp as cognitive
    from app.routes.dashboard   import dashboard
    from app.routes.youtube     import youtube_bp
    from app.routes.gemini      import gemini_bp
    from app.routes.recommend   import recommend_bp
    from app.routes.admin       import admin_bp
    from app.routes.social_auth import social_bp

    app.register_blueprint(auth)
    app.register_blueprint(cognitive)
    app.register_blueprint(dashboard)
    app.register_blueprint(youtube_bp)
    app.register_blueprint(gemini_bp)
    app.register_blueprint(recommend_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(social_bp)

    @app.route('/')
    def home():
        return redirect(url_for('auth.login'))

    return app