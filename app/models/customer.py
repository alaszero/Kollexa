"""Modelo de clientes y tokens de portal."""
import secrets
from datetime import datetime, timezone, timedelta
from app.extensions import db
from app.models.mixins import TimestampMixin, SoftDeleteMixin


class Customer(TimestampMixin, SoftDeleteMixin, db.Model):
    __tablename__ = 'customers'

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)
    neighborhood = db.Column(db.String(100), nullable=True, index=True)
    city = db.Column(db.String(100), nullable=True)
    reference = db.Column(db.Text, nullable=True)
    gps_lat = db.Column(db.Numeric(10, 8), nullable=True)
    gps_lng = db.Column(db.Numeric(11, 8), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Relaciones
    sales = db.relationship('Sale', backref='customer', lazy='dynamic')
    portal_tokens = db.relationship('CustomerPortalToken', backref='customer', lazy='dynamic')
    creator = db.relationship('User', foreign_keys=[created_by])

    def to_dict(self):
        return {
            'id': self.id,
            'full_name': self.full_name,
            'phone': self.phone,
            'address': self.address,
            'neighborhood': self.neighborhood,
            'city': self.city,
            'reference': self.reference,
            'notes': self.notes,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<Customer {self.full_name}>'


class CustomerPortalToken(db.Model):
    __tablename__ = 'customer_portal_tokens'

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    @staticmethod
    def generate_token():
        return secrets.token_urlsafe(32)

    @property
    def is_valid(self):
        if not self.is_active:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True

    def __repr__(self):
        return f'<PortalToken customer={self.customer_id}>'
