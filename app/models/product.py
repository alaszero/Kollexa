"""Modelo de productos."""
from app.extensions import db
from app.models.mixins import TimestampMixin, SoftDeleteMixin


class Product(TimestampMixin, SoftDeleteMixin, db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    base_price = db.Column(db.Numeric(10, 2), nullable=False)
    sell_price = db.Column(db.Numeric(10, 2), nullable=False)
    category = db.Column(db.String(100), nullable=True, index=True)

    # Relaciones
    stock_items = db.relationship('StockItem', backref='product', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'sku': self.sku,
            'name': self.name,
            'description': self.description,
            'base_price': str(self.base_price),
            'sell_price': str(self.sell_price),
            'category': self.category,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<Product {self.name}>'
