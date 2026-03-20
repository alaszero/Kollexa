"""Blueprints de API REST."""
from flask import Blueprint

api_bp = Blueprint('api', __name__)

from app.api import auth, health, products, inventory, customers, sales, collections  # noqa: E402, F401
