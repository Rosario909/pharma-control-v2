from flask import Blueprint

alertas_bp = Blueprint("alertas", __name__, url_prefix="/api/alertas")

from app.blueprints.alertas import routes  # noqa: E402,F401
