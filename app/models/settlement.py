"""Modelo de liquidaciones de cobradores."""
from datetime import datetime, timezone
from app.extensions import db


class AgentSettlement(db.Model):
    """Liquidacion de un cobrador: agrupa los pagos cobrados pendientes de entregar."""
    __tablename__ = 'agent_settlements'

    id = db.Column(db.Integer, primary_key=True)
    agent_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    payment_count = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, confirmed
    notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    confirmed_at = db.Column(db.DateTime, nullable=True)
    confirmed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Relaciones
    agent = db.relationship('User', foreign_keys=[agent_id], backref='settlements')
    confirmer = db.relationship('User', foreign_keys=[confirmed_by])
    details = db.relationship('SettlementDetail', backref='settlement', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'agent_id': self.agent_id,
            'total_amount': str(self.total_amount),
            'payment_count': self.payment_count,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'confirmed_at': self.confirmed_at.isoformat() if self.confirmed_at else None,
        }


class SettlementDetail(db.Model):
    """Detalle: cada pago incluido en una liquidacion."""
    __tablename__ = 'settlement_details'

    id = db.Column(db.Integer, primary_key=True)
    settlement_id = db.Column(db.Integer, db.ForeignKey('agent_settlements.id'), nullable=False)
    payment_id = db.Column(db.Integer, db.ForeignKey('payments.id'), nullable=False, unique=True)

    # Relaciones
    payment = db.relationship('Payment', backref='settlement_detail')
