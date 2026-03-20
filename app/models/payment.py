"""Modelos de plan de pagos, cuotas y pagos."""
from datetime import datetime, timezone
from app.extensions import db
from app.models.mixins import TimestampMixin


class PaymentPlan(TimestampMixin, db.Model):
    __tablename__ = 'payment_plans'

    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), unique=True, nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    num_installments = db.Column(db.Integer, nullable=False)
    installment_amount = db.Column(db.Numeric(10, 2), nullable=False)
    interest_rate = db.Column(db.Numeric(5, 2), default=0)
    penalty_rate = db.Column(db.Numeric(5, 2), default=0)
    grace_days = db.Column(db.Integer, default=0)
    start_date = db.Column(db.Date, nullable=False)
    frequency_days = db.Column(db.Integer, default=7)  # Semanal
    status = db.Column(db.String(20), default='active', nullable=False)

    # Relaciones
    installments = db.relationship(
        'PaymentInstallment', backref='plan',
        cascade='all, delete-orphan',
        order_by='PaymentInstallment.installment_num'
    )

    def to_dict(self):
        return {
            'id': self.id,
            'sale_id': self.sale_id,
            'total_amount': str(self.total_amount),
            'num_installments': self.num_installments,
            'installment_amount': str(self.installment_amount),
            'interest_rate': str(self.interest_rate),
            'penalty_rate': str(self.penalty_rate),
            'grace_days': self.grace_days,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'frequency_days': self.frequency_days,
            'status': self.status,
        }

    def __repr__(self):
        return f'<PaymentPlan sale={self.sale_id} installments={self.num_installments}>'


class PaymentInstallment(db.Model):
    __tablename__ = 'payment_installments'

    STATUSES = ('pending', 'partial', 'paid', 'overdue', 'grace')

    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('payment_plans.id'), nullable=False)
    installment_num = db.Column(db.Integer, nullable=False)
    due_date = db.Column(db.Date, nullable=False, index=True)
    expected_amount = db.Column(db.Numeric(10, 2), nullable=False)
    paid_amount = db.Column(db.Numeric(10, 2), default=0)
    penalty_amount = db.Column(db.Numeric(10, 2), default=0)
    status = db.Column(db.String(20), default='pending', nullable=False, index=True)
    paid_at = db.Column(db.DateTime, nullable=True)

    # Relaciones
    payments = db.relationship('Payment', backref='installment', cascade='all, delete-orphan')

    @property
    def remaining(self):
        return self.expected_amount + self.penalty_amount - self.paid_amount

    def to_dict(self):
        return {
            'id': self.id,
            'plan_id': self.plan_id,
            'installment_num': self.installment_num,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'expected_amount': str(self.expected_amount),
            'paid_amount': str(self.paid_amount),
            'penalty_amount': str(self.penalty_amount),
            'status': self.status,
            'remaining': str(self.remaining),
            'paid_at': self.paid_at.isoformat() if self.paid_at else None,
        }

    def __repr__(self):
        return f'<Installment #{self.installment_num} plan={self.plan_id} status={self.status}>'


class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    installment_id = db.Column(
        db.Integer, db.ForeignKey('payment_installments.id'), nullable=False
    )
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_date = db.Column(db.DateTime, nullable=False)
    collected_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    payment_method = db.Column(db.String(20), default='cash')  # 'cash', 'transfer'
    notes = db.Column(db.Text, nullable=True)
    latitude = db.Column(db.Numeric(10, 8), nullable=True)
    longitude = db.Column(db.Numeric(11, 8), nullable=True)
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relaciones
    collector = db.relationship('User', foreign_keys=[collected_by])

    def to_dict(self):
        return {
            'id': self.id,
            'installment_id': self.installment_id,
            'amount': str(self.amount),
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'collected_by': self.collected_by,
            'payment_method': self.payment_method,
            'notes': self.notes,
        }

    def __repr__(self):
        return f'<Payment ${self.amount} installment={self.installment_id}>'
