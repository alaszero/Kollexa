"""Modelos de sistema: configuración, auditoría y versionamiento."""
from datetime import datetime, timezone
from app.extensions import db


class SystemConfig(db.Model):
    """Configuración dinámica del sistema (key-value)."""
    __tablename__ = 'system_config'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=False)
    value_type = db.Column(db.String(20), default='string')  # string, int, float, bool, json
    description = db.Column(db.String(200), nullable=True)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    def get_typed_value(self):
        """Retorna el valor convertido al tipo correcto."""
        if self.value_type == 'int':
            return int(self.value)
        elif self.value_type == 'float':
            return float(self.value)
        elif self.value_type == 'bool':
            return self.value.lower() in ('true', '1', 'yes')
        elif self.value_type == 'json':
            import json
            return json.loads(self.value)
        return self.value

    def to_dict(self):
        return {
            'key': self.key,
            'value': self.get_typed_value(),
            'value_type': self.value_type,
            'description': self.description,
        }

    def __repr__(self):
        return f'<SystemConfig {self.key}={self.value}>'


class AuditLog(db.Model):
    """Registro de auditoría de todas las acciones del sistema."""
    __tablename__ = 'audit_log'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(50), nullable=False, index=True)
    entity_type = db.Column(db.String(50), nullable=True)
    entity_id = db.Column(db.Integer, nullable=True)
    old_values = db.Column(db.Text, nullable=True)  # JSON
    new_values = db.Column(db.Text, nullable=True)  # JSON
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    # Relaciones
    user = db.relationship('User', foreign_keys=[user_id])

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'action': self.action,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'ip_address': self.ip_address,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<AuditLog {self.action} entity={self.entity_type}:{self.entity_id}>'


class SystemVersion(db.Model):
    """Historial de versiones instaladas."""
    __tablename__ = 'system_versions'

    id = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.String(20), nullable=False)
    build = db.Column(db.String(50), nullable=True)
    installed_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    installed_by = db.Column(db.String(100), nullable=True)
    previous_version = db.Column(db.String(20), nullable=True)
    manifest = db.Column(db.Text, nullable=True)  # JSON del manifest completo
    status = db.Column(db.String(20), default='active')  # 'active', 'rolled_back'

    def __repr__(self):
        return f'<SystemVersion {self.version} ({self.status})>'
