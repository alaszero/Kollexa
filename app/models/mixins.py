"""Mixins reutilizables para modelos."""
from datetime import datetime, timezone
from app.extensions import db


class TimestampMixin:
    """Agrega created_at y updated_at automáticos."""
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )


class SoftDeleteMixin:
    """Agrega borrado lógico."""
    is_active = db.Column(db.Boolean, default=True, nullable=False)
