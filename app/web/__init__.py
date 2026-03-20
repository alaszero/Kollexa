"""Blueprints de vistas web."""
from flask import Blueprint

web_bp = Blueprint('web', __name__)

from app.web import auth  # noqa: E402, F401
