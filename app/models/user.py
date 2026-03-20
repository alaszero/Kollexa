"""Modelos de usuarios, roles y permisos."""
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db
from app.models.mixins import TimestampMixin, SoftDeleteMixin


# Tabla asociativa: User ↔ Role (N:M)
user_roles = db.Table(
    'user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True),
)

# Tabla asociativa: Role ↔ Permission (N:M)
role_permissions = db.Table(
    'role_permissions',
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permissions.id'), primary_key=True),
)


class User(UserMixin, TimestampMixin, SoftDeleteMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20), nullable=True)

    # Relaciones
    roles = db.relationship('Role', secondary=user_roles, backref='users', lazy='joined')
    stock_location = db.relationship('StockLocation', backref='user', uselist=False, lazy='joined')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_permission(self, permission_code):
        """Verificar si el usuario tiene un permiso específico."""
        for role in self.roles:
            for perm in role.permissions:
                if perm.code == permission_code:
                    return True
        return False

    def has_role(self, role_name):
        """Verificar si el usuario tiene un rol específico."""
        return any(r.name == role_name for r in self.roles)

    def get_permissions(self):
        """Obtener set de todos los códigos de permiso del usuario."""
        perms = set()
        for role in self.roles:
            for perm in role.permissions:
                perms.add(perm.code)
        return perms

    def to_dict(self, include_permissions=False):
        data = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'phone': self.phone,
            'is_active': self.is_active,
            'roles': [r.name for r in self.roles],
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        if include_permissions:
            data['permissions'] = list(self.get_permissions())
        return data

    def __repr__(self):
        return f'<User {self.username}>'


class Role(db.Model):
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200), nullable=True)
    is_system = db.Column(db.Boolean, default=False, nullable=False)

    permissions = db.relationship('Permission', secondary=role_permissions, backref='roles', lazy='joined')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'is_system': self.is_system,
            'permissions': [p.code for p in self.permissions],
        }

    def __repr__(self):
        return f'<Role {self.name}>'


class Permission(db.Model):
    __tablename__ = 'permissions'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(100), unique=True, nullable=False, index=True)
    module = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'module': self.module,
            'description': self.description,
        }

    def __repr__(self):
        return f'<Permission {self.code}>'
