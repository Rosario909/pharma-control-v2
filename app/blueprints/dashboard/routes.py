"""KPIs calculados en runtime. Dispara ComplianceService al cargar."""
from flask import jsonify

from app.blueprints.dashboard import dashboard_bp
from app.extensions import get_supabase
from app.security import require_role
from app.services import compliance_service

TODOS = ("admin", "compliance_officer", "gerente")


@dashboard_bp.get("/")
@require_role(*TODOS)
def kpis():
    # Recalcula estado/score/alertas antes de leer los KPIs.
    compliance_service.recalcular()

    productos = (
        get_supabase().table("productos")
        .select("estado, score_riesgo")
        .neq("estado", "inactivo")
        .execute()
        .data
    ) or []

    total = len(productos)
    por_vencer = sum(1 for p in productos if p["estado"] == "por_vencer")
    vencidos = sum(1 for p in productos if p["estado"] == "vencido")
    vigentes = sum(1 for p in productos if p["estado"] == "vigente")
    score_promedio = round(sum(p["score_riesgo"] for p in productos) / total) if total else 0

    alertas_activas = (
        get_supabase().table("alertas")
        .select("id", count="exact")
        .eq("estado", "activa")
        .execute()
        .count
    ) or 0

    return jsonify(
        total_productos=total,
        vigentes=vigentes,
        por_vencer=por_vencer,
        vencidos=vencidos,
        alertas_activas=alertas_activas,
        score_promedio=score_promedio,
    ), 200
