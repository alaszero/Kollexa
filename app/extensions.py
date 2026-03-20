"""Extensiones Flask centralizadas."""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_caching import Cache
from flask_jwt_extended import JWTManager
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
cache = Cache()
jwt = JWTManager()
csrf = CSRFProtect()

login_manager.login_view = 'web_auth.login'
login_manager.login_message = 'Inicia sesión para continuar.'
login_manager.login_message_category = 'warning'
