"""Rutas de autenticación: login / logout / refresh (cookies HttpOnly)."""
from flask import jsonify, request

from app.blueprints.auth import auth_bp
from app.config import Config
from app.security import clear_auth_cookies, set_auth_cookies
from app.services import auth_service
from app.services.auth_service import AuthError


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if not email or not password:
        return jsonify(error="email y password requeridos"), 400

    try:
        result = auth_service.login(email, password)
    except AuthError as e:
        return jsonify(error=str(e)), 401

    resp = jsonify(user=result["user"])
    set_auth_cookies(resp, result["access_token"], result["refresh_token"])
    return resp, 200


@auth_bp.post("/refresh")
def refresh():
    token = request.cookies.get(Config.COOKIE_REFRESH_NAME)
    if not token:
        return jsonify(error="no hay refresh token"), 401
    try:
        result = auth_service.refresh(token)
    except AuthError as e:
        resp = jsonify(error=str(e))
        clear_auth_cookies(resp)
        return resp, 401

    resp = jsonify(user=result["user"])
    set_auth_cookies(resp, result["access_token"], result["refresh_token"])
    return resp, 200


@auth_bp.post("/logout")
def logout():
    token = request.cookies.get(Config.COOKIE_REFRESH_NAME)
    auth_service.logout(token)
    resp = jsonify(message="sesión cerrada")
    clear_auth_cookies(resp)
    return resp, 200
