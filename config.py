import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent


class Config:
    """Configuración base."""
    APP_NAME = os.getenv('APP_NAME', 'Kollexa')
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-cambiar')

    # Base de datos
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URI',
        f'sqlite:///{BASE_DIR / "instance" / "kollexa.db"}'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
    }

    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-dev-secret-cambiar')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        seconds=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 3600))
    )

    # Caché
    CACHE_TYPE = os.getenv('CACHE_TYPE', 'SimpleCache')
    CACHE_DEFAULT_TIMEOUT = 300
    CACHE_REDIS_URL = os.getenv('CACHE_REDIS_URL', None)

    # Versión
    VERSION = (BASE_DIR / 'version.txt').read_text().strip()

    # Paginación
    DEFAULT_PAGE_SIZE = 25
    MAX_PAGE_SIZE = 100


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'connect_args': {'timeout': 30},  # SQLite WAL timeout
    }


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
}
