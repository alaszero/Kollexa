"""Blueprints de API REST."""
from flask import Blueprint

api_bp = Blueprint('api', __name__)

from app.api import auth, health  # noqa: E402, F401
