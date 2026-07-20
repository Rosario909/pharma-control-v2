"""Configuración de la aplicación (lee variables de entorno de Railway)."""
import os


class Config:
    # --- Supabase ---
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY")  # service_role

    # --- JWT ---
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
    JWT_ACCESS_EXPIRES = int(os.environ.get("JWT_ACCESS_EXPIRES", 900))        # 15 min
    JWT_REFRESH_EXPIRES = int(os.environ.get("JWT_REFRESH_EXPIRES", 604800))   # 7 días

    # --- Gemini ---
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
    GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")

    # --- Flask / entorno ---
    FLASK_ENV = os.environ.get("FLASK_ENV", "production")
    IS_PRODUCTION = FLASK_ENV == "production"

    # --- Cookies HttpOnly (auth) ---
    # access_token y refresh_token viajan en cookies HttpOnly.
    COOKIE_HTTPONLY = True
    COOKIE_SECURE = IS_PRODUCTION          # True en prod (HTTPS de Railway)
    COOKIE_SAMESITE = "Lax"                # mismo origen (Flask sirve los templates)
    COOKIE_ACCESS_NAME = "access_token"
    COOKIE_REFRESH_NAME = "refresh_token"

    # --- Reglas de compliance (umbrales de vencimiento en días) ---
    DIAS_WARNING = int(os.environ.get("DIAS_WARNING", 90))
    DIAS_CRITICAL = int(os.environ.get("DIAS_CRITICAL", 30))

    @classmethod
    def validate(cls):
        """Falla rápido si faltan variables críticas."""
        requeridas = [
            "SUPABASE_URL", "SUPABASE_KEY",
            "JWT_SECRET_KEY", "GEMINI_API_KEY",
        ]
        faltantes = [v for v in requeridas if not getattr(cls, v)]
        if faltantes:
            raise RuntimeError(
                f"Faltan variables de entorno: {', '.join(faltantes)}"
            )
