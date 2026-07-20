"""Extensiones compartidas: cliente Supabase único para toda la app."""
from supabase import create_client, Client

from app.config import Config

# Se inicializa en create_app() vía init_supabase().
supabase: Client | None = None


def init_supabase() -> Client:
    """Crea (una sola vez) el cliente Supabase con la service_role key."""
    global supabase
    if supabase is None:
        supabase = create_client(Config.SUPABASE_URL.strip(), Config.SUPABASE_KEY.strip())
    return supabase


def get_supabase() -> Client:
    """Devuelve el cliente ya inicializado (úsalo en services/blueprints)."""
    if supabase is None:
        raise RuntimeError("Supabase no inicializado. Llama init_supabase() en create_app().")
    return supabase
