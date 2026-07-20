"""Seguridad de peticiones: cookies HttpOnly + decorador @require_role.

- Las cookies access_token / refresh_token son HttpOnly (no accesibles por JS).
- @require_role valida el access token de la cookie y el rol del usuario.
  En rutas /api responde 401/403 JSON; en páginas redirige a /login.
"""
from __future__ import annotations

from functools import wraps

from flask import g, jsonify, redirect, request, url_for

from app.config import Config
from app.services.auth_service import AuthError, decode_access_token


# --------------------------------------------------------------------------
# Cookies
# --------------------------------------------------------------------------
def set_auth_cookies(response, access_token: str, refresh_token: str):
    common = {
        "httponly": Config.COOKIE_HTTPONLY,
        "secure": Config.COOKIE_SECURE,
        "samesite": Config.COOKIE_SAMESITE,
        "path": "/",
    }
    response.set_cookie(
        Config.COOKIE_ACCESS_NAME, access_token,
        max_age=Config.JWT_ACCESS_EXPIRES, **common,
    )
    response.set_cookie(
        Config.COOKIE_REFRESH_NAME, refresh_token,
        max_age=Config.JWT_REFRESH_EXPIRES, **common,
    )
    return response


def clear_auth_cookies(response):
    response.delete_cookie(Config.COOKIE_ACCESS_NAME, path="/")
    response.delete_cookie(Config.COOKIE_REFRESH_NAME, path="/")
    return response


# --------------------------------------------------------------------------
# Decorador de autorización
# --------------------------------------------------------------------------
def _is_api_request() -> bool:
    return request.path.startswith("/api/")


def _deny(message: str, status: int):
    if _is_api_request():
        return jsonify(error=message), status
    return redirect(url_for("web.login"))


def require_role(*roles: str):
    """Exige sesión válida y, opcionalmente, uno de los roles indicados.

    Uso:
        @require_role()                      -> cualquier usuario autenticado
        @require_role("admin")               -> solo admin
        @require_role("admin", "compliance_officer")
    """
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            token = request.cookies.get(Config.COOKIE_ACCESS_NAME)
            if not token:
                return _deny("no autenticado", 401)
            try:
                payload = decode_access_token(token)
            except AuthError as e:
                return _deny(str(e), 401)

            if roles and payload.get("role") not in roles:
                return _deny("permiso denegado", 403)

            # Disponible para la vista vía g.current_user
            g.current_user = {
                "id": payload["sub"],
                "email": payload["email"],
                "role": payload["role"],
            }
            return view(*args, **kwargs)

        return wrapper

    return decorator
