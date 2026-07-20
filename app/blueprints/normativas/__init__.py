from flask import Blueprint

normativas_bp = Blueprint("normativas", __name__, url_prefix="/api/normativas")

from app.blueprints.normativas import routes  # noqa: E402,F401
