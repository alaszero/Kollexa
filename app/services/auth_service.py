"""Servicio de autenticación."""
from app.extensions import db
from app.models.user import User
from app.utils.audit import log_action


def authenticate_user(username, password):
    """Autenticar usuario por username y password.

    Returns:
        User o None
    """
    user = User.query.filter_by(username=username).first()
    if user and user.is_active and user.check_password(password):
        return user
    return None


def create_user(username, password, full_name, email=None, phone=None, role_names=None):
    """Crear un nuevo usuario.

    Args:
        role_names: lista de nombres de rol, ej: ['agent']

    Returns:
        User creado
    """
    from app.models.user import Role

    user = User(
        username=username,
        full_name=full_name,
        email=email,
        phone=phone,
    )
    user.set_password(password)

    if role_names:
        roles = Role.query.filter(Role.name.in_(role_names)).all()
        user.roles = roles

    db.session.add(user)
    db.session.flush()

    # Crear stock location si es agente
    if role_names and 'agent' in role_names:
        from app.models.inventory import StockLocation
        location = StockLocation(
            type='agent',
            name=f'Stock de {full_name}',
            user_id=user.id,
        )
        db.session.add(location)

    db.session.commit()
    return user


def update_user(user, **kwargs):
    """Actualizar datos de un usuario."""
    allowed_fields = ('full_name', 'email', 'phone', 'is_active')
    for field in allowed_fields:
        if field in kwargs:
            setattr(user, field, kwargs[field])

    if 'password' in kwargs and kwargs['password']:
        user.set_password(kwargs['password'])

    if 'role_names' in kwargs:
        from app.models.user import Role
        roles = Role.query.filter(Role.name.in_(kwargs['role_names'])).all()
        user.roles = roles

    db.session.commit()
    return user
