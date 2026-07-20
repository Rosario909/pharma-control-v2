from flask import Blueprint

productos_bp = Blueprint("productos", __name__, url_prefix="/api/productos")

from app.blueprints.productos import routes  # noqa: E402,F401
