"""ComplianceService — motor de cumplimiento por vencimiento.

recalcular() corre en runtime (lo disparan dashboard y alertas):
  1. Para cada producto activo calcula días restantes hasta el vencimiento
     del registro sanitario.
  2. Deriva estado ('vigente' | 'por_vencer' | 'vencido') y score_riesgo (0-100),
     y los persiste en `productos` si cambiaron.
  3. Genera/actualiza una alerta por producto que lo necesite (upsert idempotente
     sobre (producto_id, tipo)). Si el producto vuelve a estar vigente, marca su
     alerta como 'resuelta'.

Umbrales configurables en Config: DIAS_WARNING (90) y DIAS_CRITICAL (30).
"""
from __future__ import annotations

from datetime import date

from app.config import Config
from app.extensions import get_supabase

TIPO_ALERTA = "vencimiento_registro"


def _evaluar(dias: int) -> tuple[str, int, str | None]:
    """Devuelve (estado, score_riesgo, severidad). severidad None = sin alerta."""
    if dias < 0:
        return "vencido", 100, "critical"
    if dias <= Config.DIAS_CRITICAL:
        return "por_vencer", 80, "critical"
    if dias <= Config.DIAS_WARNING:
        return "por_vencer", 50, "warning"
    return "vigente", 10, None


def _mensaje(dias: int) -> str:
    if dias < 0:
        return f"Registro sanitario vencido hace {abs(dias)} días."
    if dias == 0:
        return "El registro sanitario vence hoy."
    return f"El registro sanitario vence en {dias} días."


def recalcular() -> dict:
    """Recalcula estado/score y sincroniza alertas. Devuelve un resumen."""
    sb = get_supabase()
    hoy = date.today()

    productos = (
        sb.table("productos")
        .select("id, fecha_vencimiento, estado, score_riesgo")
        .neq("estado", "inactivo")
        .execute()
        .data
    ) or []

    actualizados = 0
    alertas_activas = 0

    for p in productos:
        dias = (date.fromisoformat(p["fecha_vencimiento"]) - hoy).days
        estado, score, severidad = _evaluar(dias)

        # 1) Persistir cambios en el producto.
        if p["estado"] != estado or p["score_riesgo"] != score:
            sb.table("productos").update(
                {"estado": estado, "score_riesgo": score}
            ).eq("id", p["id"]).execute()
            actualizados += 1

        # 2) Sincronizar alerta.
        if severidad:
            sb.table("alertas").upsert(
                {
                    "producto_id": p["id"],
                    "tipo": TIPO_ALERTA,
                    "severidad": severidad,
                    "mensaje": _mensaje(dias),
                    "dias_restantes": dias,
                    "estado": "activa",
                },
                on_conflict="producto_id,tipo",
            ).execute()
            alertas_activas += 1
        else:
            # Producto sano: resuelve su alerta si existía.
            sb.table("alertas").update({"estado": "resuelta"}).eq(
                "producto_id", p["id"]
            ).eq("tipo", TIPO_ALERTA).execute()

    return {
        "productos_evaluados": len(productos),
        "productos_actualizados": actualizados,
        "alertas_activas": alertas_activas,
    }
