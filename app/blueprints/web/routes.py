"""Páginas HTML (Jinja2). Mismo origen que la API → cookies HttpOnly.

Roles:
  - admin / compliance_officer: todo
  - gerente: solo lectura (dashboard, alertas, chatbot)
"""
from flask import g, redirect, render_template, url_for

from app.blueprints.web import web_bp
from app.security import require_role

TODOS = ("admin", "compliance_officer", "gerente")
GESTORES = ("admin", "compliance_officer")


@web_bp.get("/login")
def login():
    return render_template("login.html")


@web_bp.get("/")
def index():
    return redirect(url_for("web.dashboard"))


@web_bp.get("/dashboard")
@require_role(*TODOS)
def dashboard():
    return render_template("dashboard.html", user=g.current_user)


@web_bp.get("/productos")
@require_role(*GESTORES)
def productos():
    return render_template("productos.html", user=g.current_user)


@web_bp.get("/normativas")
@require_role(*GESTORES)
def normativas():
    return render_template("normativas.html", user=g.current_user)


@web_bp.get("/alertas")
@require_role(*TODOS)
def alertas():
    return render_template("alertas.html", user=g.current_user)


@web_bp.get("/chatbot")
@require_role(*TODOS)
def chatbot():
    return render_template("chatbot.html", user=g.current_user)
