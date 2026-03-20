"""Servicio de verificación de permisos."""
from functools import wraps
from flask import abort
from flask_login import current_user


def check_permission(user, permission_code):
    """Verificar si un usuario tiene un permiso específico.

    Superadmin tiene todos los permisos automáticamente.
    """
    if user.has_role('superadmin'):
        return True
    return user.has_permission(permission_code)


def check_any_permission(user, *permission_codes):
    """Verificar si el usuario tiene AL MENOS UNO de los permisos."""
    if user.has_role('superadmin'):
        return True
    return any(user.has_permission(code) for code in permission_codes)


def check_all_permissions(user, *permission_codes):
    """Verificar si el usuario tiene TODOS los permisos."""
    if user.has_role('superadmin'):
        return True
    return all(user.has_permission(code) for code in permission_codes)


def get_user_modules(user):
    """Obtener los módulos a los que el usuario tiene acceso."""
    if user.has_role('superadmin'):
        return {'all'}
    modules = set()
    for role in user.roles:
        for perm in role.permissions:
            modules.add(perm.module)
    return modules
