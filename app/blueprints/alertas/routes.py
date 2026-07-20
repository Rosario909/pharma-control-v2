"""Alertas — versión simple.

GET /api/alertas: recalcula compliance y devuelve las alertas activas
(con el nombre del producto), las críticas primero.
"""
from flask import jsonify

from app.blueprints.alertas import alertas_bp
from app.extensions import get_supabase
from app.security import require_role
from app.services import compliance_service

TODOS = ("admin", "compliance_officer", "gerente")
ORDEN = {"critical": 0, "warning": 1, "info": 2}


@alertas_bp.get("/")
@require_role(*TODOS)
def listar():
    compliance_service.recalcular()

    alertas = (
        get_supabase().table("alertas")
        .select("id, tipo, severidad, mensaje, dias_restantes, productos(nombre, registro_sanitario)")
        .eq("estado", "activa")
        .execute()
        .data
    ) or []

    alertas.sort(key=lambda a: (ORDEN.get(a["severidad"], 9), a.get("dias_restantes", 0)))
    return jsonify(alertas=alertas), 200
