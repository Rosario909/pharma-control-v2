"""Catálogo de NOMs (alta manual). Acceso: admin y compliance_officer."""
from flask import jsonify, request

from app.blueprints.normativas import normativas_bp
from app.extensions import get_supabase
from app.security import require_role

GESTORES = ("admin", "compliance_officer")
CAMPOS = ("codigo", "titulo", "descripcion", "url", "vigente")


@normativas_bp.get("/")
@require_role(*GESTORES)
def listar():
    data = (
        get_supabase().table("normativas")
        .select("*").order("codigo").execute().data
    )
    return jsonify(normativas=data or []), 200


@normativas_bp.post("/")
@require_role(*GESTORES)
def crear():
    body = request.get_json(silent=True) or {}
    codigo = (body.get("codigo") or "").strip()
    titulo = (body.get("titulo") or "").strip()
    if not codigo or not titulo:
        return jsonify(error="codigo y titulo son obligatorios"), 400

    row = {k: body[k] for k in CAMPOS if body.get(k) not in (None, "")}
    try:
        res = get_supabase().table("normativas").insert(row).execute()
    except Exception as e:  # codigo duplicado
        return jsonify(error="no se pudo crear la normativa", detalle=str(e)), 409
    return jsonify(normativa=res.data[0]), 201


@normativas_bp.delete("/<uuid:normativa_id>")
@require_role(*GESTORES)
def eliminar(normativa_id):
    res = (
        get_supabase().table("normativas")
        .delete().eq("id", str(normativa_id)).execute()
    )
    if not res.data:
        return jsonify(error="normativa no encontrada"), 404
    return jsonify(message="normativa eliminada"), 200
