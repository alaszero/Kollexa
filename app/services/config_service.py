"""Servicio de configuración dinámica del sistema."""
from app.extensions import db, cache
from app.models.system import SystemConfig


def get_config(key, default=None):
    """Obtener un valor de configuración por su clave."""
    cached = cache.get(f'config:{key}')
    if cached is not None:
        return cached

    config = SystemConfig.query.filter_by(key=key).first()
    if config is None:
        return default

    value = config.get_typed_value()
    cache.set(f'config:{key}', value, timeout=300)
    return value


def set_config(key, value, value_type='string', description=None, user_id=None):
    """Establecer un valor de configuración."""
    config = SystemConfig.query.filter_by(key=key).first()

    if config is None:
        config = SystemConfig(key=key)
        db.session.add(config)

    config.value = str(value)
    config.value_type = value_type
    if description:
        config.description = description
    config.updated_by = user_id

    db.session.commit()
    cache.delete(f'config:{key}')
    return config


def get_all_config():
    """Obtener todas las configuraciones como dict."""
    configs = SystemConfig.query.all()
    return {c.key: c.get_typed_value() for c in configs}


# Helpers para configuraciones frecuentes
def is_interest_enabled():
    return get_config('interest_enabled', default=False)


def is_penalty_enabled():
    return get_config('penalty_enabled', default=False)


def get_default_grace_days():
    return get_config('default_grace_days', default=0)


def get_default_interest_rate():
    return get_config('default_interest_rate', default=0.0)


def get_collection_mode():
    """'agent' = el vendedor cobra, 'collector' = cobrador dedicado."""
    return get_config('collection_mode', default='agent')
