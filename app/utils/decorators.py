"""Decoradores para control de acceso."""
from functools import wraps
from flask import abort, jsonify, request
from flask_login import current_user
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity


def permission_required(*permission_codes):
    """Decorador: requiere uno o más permisos.

    Uso:
        @permission_required('sales.create')
        @permission_required('inventory.view', 'inventory.edit')  # requiere TODOS
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.has_role('superadmin'):
                return f(*args, **kwargs)
            for code in permission_codes:
                if not current_user.has_permission(code):
                    abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def role_required(*role_names):
    """Decorador: requiere uno de los roles indicados.

    Uso:
        @role_required('admin', 'superadmin')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if not any(current_user.has_role(r) for r in role_names):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def api_auth_required(f):
    """Decorador para endpoints API: verifica JWT y carga el usuario."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        from app.models.user import User
        from app.extensions import db
        user = db.session.get(User, int(user_id))
        if not user or not user.is_active:
            return jsonify({'error': 'Usuario no válido o inactivo'}), 401
        kwargs['current_api_user'] = user
        return f(*args, **kwargs)
    return decorated_function


def api_permission_required(*permission_codes):
    """Decorador para endpoints API: verifica JWT + permisos."""
    def decorator(f):
        @wraps(f)
        @api_auth_required
        def decorated_function(*args, **kwargs):
            user = kwargs['current_api_user']
            if user.has_role('superadmin'):
                return f(*args, **kwargs)
            for code in permission_codes:
                if not user.has_permission(code):
                    return jsonify({'error': f'Permiso requerido: {code}'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator
