"""Modelos de ventas."""
from app.extensions import db
from app.models.mixins import TimestampMixin


class Sale(TimestampMixin, db.Model):
    __tablename__ = 'sales'

    STATUSES = ('active', 'completed', 'cancelled', 'defaulted')

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False, index=True)
    agent_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    stock_location_id = db.Column(
        db.Integer, db.ForeignKey('stock_locations.id'), nullable=False
    )
    sale_date = db.Column(db.Date, nullable=False)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    interest_total = db.Column(db.Numeric(10, 2), default=0)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    num_installments = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='active', nullable=False, index=True)
    notes = db.Column(db.Text, nullable=True)

    # Relaciones
    agent = db.relationship('User', foreign_keys=[agent_id], backref='sales')
    stock_location = db.relationship('StockLocation', foreign_keys=[stock_location_id])
    details = db.relationship('SaleDetail', backref='sale', cascade='all, delete-orphan')
    payment_plan = db.relationship('PaymentPlan', backref='sale', uselist=False)

    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'agent_id': self.agent_id,
            'sale_date': self.sale_date.isoformat() if self.sale_date else None,
            'subtotal': str(self.subtotal),
            'interest_total': str(self.interest_total),
            'total': str(self.total),
            'num_installments': self.num_installments,
            'status': self.status,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<Sale {self.id} customer={self.customer_id} total={self.total}>'


class SaleDetail(db.Model):
    __tablename__ = 'sale_details'

    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    line_total = db.Column(db.Numeric(10, 2), nullable=False)

    # Relaciones
    product = db.relationship('Product', backref='sale_details')

    def to_dict(self):
        return {
            'id': self.id,
            'sale_id': self.sale_id,
            'product_id': self.product_id,
            'quantity': self.quantity,
            'unit_price': str(self.unit_price),
            'line_total': str(self.line_total),
        }

    def __repr__(self):
        return f'<SaleDetail sale={self.sale_id} product={self.product_id}>'
