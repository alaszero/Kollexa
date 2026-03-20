"""Kollexa - Micro ERP de Cambaceo."""
import os
from flask import Flask
from config import config_by_name


def create_app(config_name=None):
    """Application factory."""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_by_name[config_name])

    # Asegurar que instance/ existe (para SQLite)
    os.makedirs(app.instance_path, exist_ok=True)

    # Inicializar extensiones
    _init_extensions(app)

    # Registrar blueprints
    _register_blueprints(app)

    # Registrar error handlers
    _register_error_handlers(app)

    # Configurar SQLite WAL mode si aplica
    _configure_sqlite(app)

    return app


def _init_extensions(app):
    from app.extensions import db, migrate, login_manager, cache, jwt, csrf

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    cache.init_app(app)
    jwt.init_app(app)
    csrf.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User
        return db.session.get(User, int(user_id))


def _register_blueprints(app):
    from app.api import api_bp
    from app.web import web_bp
    from app.web.auth import web_auth_bp
    from app.web.products import products_bp
    from app.web.inventory import inventory_bp
    from app.web.customers import customers_bp
    from app.web.sales import sales_bp

    app.register_blueprint(api_bp, url_prefix='/api/v1')
    app.register_blueprint(web_bp)
    app.register_blueprint(web_auth_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(sales_bp)


def _register_error_handlers(app):
    from app.errors.handlers import register_handlers
    register_handlers(app)


def _configure_sqlite(app):
    """Habilitar WAL mode en SQLite para mejor concurrencia."""
    if 'sqlite' in app.config.get('SQLALCHEMY_DATABASE_URI', ''):
        from sqlalchemy import event

        with app.app_context():
            from app.extensions import db
            engine = db.engine

        @event.listens_for(engine, 'connect')
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute('PRAGMA journal_mode=WAL')
            cursor.execute('PRAGMA foreign_keys=ON')
            cursor.execute('PRAGMA busy_timeout=30000')
            cursor.close()
