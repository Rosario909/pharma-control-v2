from flask import Blueprint

chatbot_bp = Blueprint("chatbot", __name__, url_prefix="/api/chatbot")

from app.blueprints.chatbot import routes  # noqa: E402,F401
