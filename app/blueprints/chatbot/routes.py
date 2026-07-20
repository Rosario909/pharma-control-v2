"""Chatbot: recibe pregunta, construye contexto desde BD, llama Gemini."""
from flask import jsonify, request

from app.blueprints.chatbot import chatbot_bp
from app.security import require_role
from app.services import chatbot_service
from app.services.chatbot_service import ChatbotError

TODOS = ("admin", "compliance_officer", "gerente")


@chatbot_bp.post("/")
@require_role(*TODOS)
def preguntar():
    body = request.get_json(silent=True) or {}
    pregunta = (body.get("pregunta") or "").strip()
    if not pregunta:
        return jsonify(error="la pregunta es obligatoria"), 400
    try:
        respuesta = chatbot_service.responder(pregunta)
    except ChatbotError as e:
        return jsonify(error=str(e)), 502
    return jsonify(respuesta=respuesta), 200
