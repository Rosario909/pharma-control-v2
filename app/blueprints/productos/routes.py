"""CRUD de productos (registro sanitario + vencimientos).

Acceso: admin y compliance_officer. El gerente es solo lectura del dashboard
y alertas, así que no entra aquí.
"""
from flask import jsonify, request

from app.blueprints.productos import productos_bp
from app.extensions import get_supabase
from app.security import require_role

GESTORES = ("admin", "compliance_officer")
CAMPOS = ("nombre", "registro_sanitario", "lote", "fecha_registro", "fecha_vencimiento")


@productos_bp.get("/")
@require_role(*GESTORES)
def listar():
    data = (
        get_supabase().table("productos")
        .select("*")
        .order("fecha_vencimiento")
        .execute()
        .data
    )
    return jsonify(productos=data or []), 200


@productos_bp.post("/")
@require_role(*GESTORES)
def crear():
    body = request.get_json(silent=True) or {}
    nombre = (body.get("nombre") or "").strip()
    registro = (body.get("registro_sanitario") or "").strip()
    vencimiento = (body.get("fecha_vencimiento") or "").strip()
    if not nombre or not registro or not vencimiento:
        return jsonify(error="nombre, registro_sanitario y fecha_vencimiento son obligatorios"), 400

    row = {k: body[k] for k in CAMPOS if body.get(k) not in (None, "")}
    try:
        res = get_supabase().table("productos").insert(row).execute()
    except Exception as e:  # registro_sanitario duplicado, etc.
        return jsonify(error="no se pudo crear el producto", detalle=str(e)), 409
    return jsonify(producto=res.data[0]), 201


@productos_bp.get("/<uuid:producto_id>")
@require_role(*GESTORES)
def detalle(producto_id):
    data = (
        get_supabase().table("productos")
        .select("*").eq("id", str(producto_id)).limit(1).execute().data
    )
    if not data:
        return jsonify(error="producto no encontrado"), 404
    return jsonify(producto=data[0]), 200


@productos_bp.put("/<uuid:producto_id>")
@require_role(*GESTORES)
def actualizar(producto_id):
    body = request.get_json(silent=True) or {}
    cambios = {k: body[k] for k in CAMPOS if k in body}
    if not cambios:
        return jsonify(error="nada para actualizar"), 400
    res = (
        get_supabase().table("productos")
        .update(cambios).eq("id", str(producto_id)).execute()
    )
    if not res.data:
        return jsonify(error="producto no encontrado"), 404
    return jsonify(producto=res.data[0]), 200


@productos_bp.delete("/<uuid:producto_id>")
@require_role(*GESTORES)
def eliminar(producto_id):
    res = (
        get_supabase().table("productos")
        .delete().eq("id", str(producto_id)).execute()
    )
    if not res.data:
        return jsonify(error="producto no encontrado"), 404
    return jsonify(message="producto eliminado"), 200
