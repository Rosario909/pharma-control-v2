from flask import Blueprint

# Sin url_prefix: sirve las páginas en la raíz (/login, /dashboard, ...).
web_bp = Blueprint("web", __name__)

from app.blueprints.web import routes  # noqa: E402,F401
