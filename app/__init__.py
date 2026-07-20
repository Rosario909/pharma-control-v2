"""Application factory de Pharma Control."""
from flask import Flask, jsonify

from app.config import Config
from app.extensions import init_supabase


def create_app(config_class: type[Config] = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Falla rápido si faltan env vars críticas.
    config_class.validate()

    # Cliente Supabase (service_role) compartido.
    init_supabase()

    _register_blueprints(app)
    _register_healthcheck(app)

    return app


def _register_blueprints(app: Flask) -> None:
    from app.blueprints.auth import auth_bp
    from app.blueprints.dashboard import dashboard_bp
    from app.blueprints.productos import productos_bp
    from app.blueprints.normativas import normativas_bp
    from app.blueprints.alertas import alertas_bp
    from app.blueprints.chatbot import chatbot_bp
    from app.blueprints.web import web_bp

    for bp in (auth_bp, dashboard_bp, productos_bp,
               normativas_bp, alertas_bp, chatbot_bp, web_bp):
        app.register_blueprint(bp)


def _register_healthcheck(app: Flask) -> None:
    @app.get("/health")
    def health():
        return jsonify(status="ok", service="pharma-control"), 200
