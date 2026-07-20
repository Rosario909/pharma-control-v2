"""ChatbotService — asistente regulatorio con context builder.

Flujo (consultas puntuales, sin historial):
  1. recalcular() para tener estados/alertas al día.
  2. _construir_contexto(): arma un resumen compacto desde Supabase
     (productos por estado, próximos a vencer, alertas activas, NOMs vigentes).
  3. responder(): inyecta el contexto + la pregunta en un prompt y llama Gemini.

La llamada a Gemini está aislada en _llamar_gemini() para poder testear el
resto sin tocar la API real.
"""
from __future__ import annotations

from datetime import date

from app.config import Config
from app.extensions import get_supabase
from app.services import compliance_service

SYSTEM_PROMPT = (
    "Eres el asistente regulatorio de PharmaControl, un sistema de monitoreo de "
    "cumplimiento farmacéutico. Respondes en español, de forma clara y concisa. "
    "Usa ÚNICAMENTE la información del contexto para responder sobre productos, "
    "vencimientos de registro sanitario, alertas y normativas (NOMs). Si la "
    "respuesta no está en el contexto, dilo honestamente y no inventes datos."
)

MAX_LISTA = 15


class ChatbotError(Exception):
    """Error al generar la respuesta del chatbot."""


def _construir_contexto() -> str:
    """Resumen compacto del estado actual del sistema desde Supabase."""
    sb = get_supabase()

    productos = (
        sb.table("productos")
        .select("nombre, registro_sanitario, fecha_vencimiento, estado, score_riesgo")
        .neq("estado", "inactivo")
        .execute()
        .data
    ) or []

    total = len(productos)
    por_estado = {"vigente": 0, "por_vencer": 0, "vencido": 0}
    for p in productos:
        por_estado[p["estado"]] = por_estado.get(p["estado"], 0) + 1

    # Productos que requieren atención, ordenados por cercanía de vencimiento.
    riesgo = sorted(
        [p for p in productos if p["estado"] in ("por_vencer", "vencido")],
        key=lambda p: p["fecha_vencimiento"],
    )[:MAX_LISTA]

    alertas = (
        sb.table("alertas")
        .select("severidad, mensaje, productos(nombre)")
        .eq("estado", "activa")
        .execute()
        .data
    ) or []

    normativas = (
        sb.table("normativas")
        .select("codigo, titulo")
        .eq("vigente", True)
        .execute()
        .data
    ) or []

    lineas = [
        f"Fecha actual: {date.today().isoformat()}",
        f"Total de productos: {total} "
        f"(vigentes: {por_estado.get('vigente',0)}, "
        f"por vencer: {por_estado.get('por_vencer',0)}, "
        f"vencidos: {por_estado.get('vencido',0)}).",
    ]

    if riesgo:
        lineas.append("\nProductos que requieren atención:")
        for p in riesgo:
            lineas.append(
                f"- {p['nombre']} (registro {p['registro_sanitario']}): "
                f"{p['estado']}, vence {p['fecha_vencimiento']}, score {p['score_riesgo']}."
            )

    if alertas:
        lineas.append(f"\nAlertas activas ({len(alertas)}):")
        for a in alertas[:MAX_LISTA]:
            prod = a["productos"]["nombre"] if a.get("productos") else "—"
            lineas.append(f"- [{a['severidad']}] {prod}: {a['mensaje']}")

    if normativas:
        lineas.append("\nNormativas vigentes (NOMs):")
        for n in normativas[:MAX_LISTA]:
            lineas.append(f"- {n['codigo']}: {n['titulo']}")

    return "\n".join(lineas)


def _llamar_gemini(prompt: str) -> str:
    """Llama a la API de Gemini. Aislada para facilitar pruebas."""
    import google.generativeai as genai

    genai.configure(api_key=Config.GEMINI_API_KEY)
    model = genai.GenerativeModel(Config.GEMINI_MODEL)
    resp = model.generate_content(prompt)
    return (resp.text or "").strip()


def responder(pregunta: str) -> str:
    """Genera la respuesta del asistente para una pregunta puntual."""
    pregunta = (pregunta or "").strip()
    if not pregunta:
        raise ChatbotError("La pregunta está vacía.")

    # Estado al día antes de construir el contexto.
    compliance_service.recalcular()
    contexto = _construir_contexto()

    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"=== CONTEXTO ===\n{contexto}\n\n"
        f"=== PREGUNTA ===\n{pregunta}\n\n"
        f"Responde usando solo el contexto anterior."
    )

    try:
        return _llamar_gemini(prompt)
    except Exception as e:
        raise ChatbotError(f"No se pudo generar la respuesta: {e}")
