"""AuthService — login, JWT de acceso y refresh tokens con rotación.

Flujo:
  - login(email, password) -> valida credenciales, emite access (JWT corto) y
    refresh (token aleatorio; en BD se guarda solo su hash sha256).
  - refresh(token) -> valida el refresh, lo revoca (rotación) y emite un par nuevo.
  - logout(token) -> revoca el refresh token.

Las cookies HttpOnly las setean las rutas del blueprint auth, no este servicio.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import Config
from app.extensions import get_supabase


# --------------------------------------------------------------------------
# Errores de dominio
# --------------------------------------------------------------------------
class AuthError(Exception):
    """Error de autenticación (credenciales/refresh inválidos)."""


# --------------------------------------------------------------------------
# Helpers de contraseña
# --------------------------------------------------------------------------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


# --------------------------------------------------------------------------
# Helpers de tokens
# --------------------------------------------------------------------------
def _now() -> datetime:
    return datetime.now(timezone.utc)


def _create_access_token(user: dict) -> str:
    payload = {
        "sub": user["id"],
        "email": user["email"],
        "role": user["role"],
        "type": "access",
        "iat": _now(),
        "exp": _now() + timedelta(seconds=Config.JWT_ACCESS_EXPIRES),
    }
    return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    """Devuelve el payload o lanza AuthError si es inválido/expirado."""
    try:
        payload = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise AuthError("access token expirado")
    except jwt.InvalidTokenError:
        raise AuthError("access token inválido")
    if payload.get("type") != "access":
        raise AuthError("tipo de token inválido")
    return payload


def _hash_refresh(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _issue_refresh_token(user_id: str) -> str:
    """Genera un refresh token, guarda su hash en BD y devuelve el token en claro."""
    token = secrets.token_urlsafe(48)
    expires_at = _now() + timedelta(seconds=Config.JWT_REFRESH_EXPIRES)
    get_supabase().table("refresh_tokens").insert({
        "user_id": user_id,
        "token_hash": _hash_refresh(token),
        "expires_at": expires_at.isoformat(),
        "revoked": False,
    }).execute()
    return token


# --------------------------------------------------------------------------
# Operaciones públicas
# --------------------------------------------------------------------------
def login(email: str, password: str) -> dict:
    """Valida credenciales. Devuelve {access_token, refresh_token, user}."""
    res = (
        get_supabase().table("users")
        .select("id, email, password_hash, nombre, role, activo")
        .eq("email", email)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    if not rows:
        raise AuthError("credenciales inválidas")

    user = rows[0]
    if not user["activo"]:
        raise AuthError("usuario inactivo")
    if not verify_password(password, user["password_hash"]):
        raise AuthError("credenciales inválidas")

    access = _create_access_token(user)
    refresh = _issue_refresh_token(user["id"])
    return {
        "access_token": access,
        "refresh_token": refresh,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "nombre": user["nombre"],
            "role": user["role"],
        },
    }


def refresh(refresh_token: str) -> dict:
    """Rota el refresh token y emite un par nuevo."""
    sb = get_supabase()
    token_hash = _hash_refresh(refresh_token)
    res = (
        sb.table("refresh_tokens")
        .select("id, user_id, expires_at, revoked")
        .eq("token_hash", token_hash)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    if not rows:
        raise AuthError("refresh token inválido")

    rt = rows[0]
    if rt["revoked"]:
        raise AuthError("refresh token revocado")
    if datetime.fromisoformat(rt["expires_at"]) < _now():
        raise AuthError("refresh token expirado")

    # Rotación: revoca el actual.
    sb.table("refresh_tokens").update({"revoked": True}).eq("id", rt["id"]).execute()

    user_res = (
        sb.table("users")
        .select("id, email, nombre, role, activo")
        .eq("id", rt["user_id"])
        .limit(1)
        .execute()
    )
    urows = user_res.data or []
    if not urows or not urows[0]["activo"]:
        raise AuthError("usuario inválido")

    user = urows[0]
    return {
        "access_token": _create_access_token(user),
        "refresh_token": _issue_refresh_token(user["id"]),
        "user": {
            "id": user["id"],
            "email": user["email"],
            "nombre": user["nombre"],
            "role": user["role"],
        },
    }


def logout(refresh_token: str | None) -> None:
    """Revoca el refresh token (si existe). Idempotente."""
    if not refresh_token:
        return
    get_supabase().table("refresh_tokens").update({"revoked": True}).eq(
        "token_hash", _hash_refresh(refresh_token)
    ).execute()
