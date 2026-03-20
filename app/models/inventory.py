"""Modelos de inventario: ubicaciones, stock y movimientos."""
from datetime import datetime, timezone
from app.extensions import db


class StockLocation(db.Model):
    """Ubicación de inventario: almacén o stock de agente."""
    __tablename__ = 'stock_locations'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), nullable=False, index=True)  # 'warehouse', 'agent'
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # NULL si warehouse
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relaciones
    stock_items = db.relationship('StockItem', backref='location', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'name': self.name,
            'user_id': self.user_id,
            'is_active': self.is_active,
        }

    def __repr__(self):
        return f'<StockLocation {self.type}:{self.name}>'


class StockItem(db.Model):
    """Stock actual de un producto en una ubicación específica."""
    __tablename__ = 'stock_items'
    __table_args__ = (
        db.UniqueConstraint('location_id', 'product_id', name='uq_location_product'),
    )

    id = db.Column(db.Integer, primary_key=True)
    location_id = db.Column(db.Integer, db.ForeignKey('stock_locations.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def to_dict(self):
        return {
            'id': self.id,
            'location_id': self.location_id,
            'product_id': self.product_id,
            'quantity': self.quantity,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<StockItem loc={self.location_id} prod={self.product_id} qty={self.quantity}>'


class InventoryMovement(db.Model):
    """Journal de movimientos de inventario. Fuente de verdad para auditoría."""
    __tablename__ = 'inventory_movements'

    TYPES = (
        'purchase',             # Compra → entra al almacén
        'dispatch',             # Surtido: almacén → agente
        'return_to_warehouse',  # Agente devuelve → almacén
        'sale',                 # Agente vende → sale del inventario
        'sale_direct',          # Venta directa desde almacén
        'adjustment_in',        # Ajuste positivo
        'adjustment_out',       # Ajuste negativo (merma/pérdida)
        'transfer',             # Agente → agente (futuro)
    )

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)  # Siempre positivo
    movement_type = db.Column(db.String(25), nullable=False, index=True)
    from_location_id = db.Column(db.Integer, db.ForeignKey('stock_locations.id'), nullable=True)
    to_location_id = db.Column(db.Integer, db.ForeignKey('stock_locations.id'), nullable=True)
    reference_type = db.Column(db.String(20), nullable=True)  # 'sale','manual','return'
    reference_id = db.Column(db.Integer, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    performed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    # Relaciones
    product = db.relationship('Product', backref='movements')
    from_location = db.relationship('StockLocation', foreign_keys=[from_location_id])
    to_location = db.relationship('StockLocation', foreign_keys=[to_location_id])
    performer = db.relationship('User', foreign_keys=[performed_by])

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'quantity': self.quantity,
            'movement_type': self.movement_type,
            'from_location_id': self.from_location_id,
            'to_location_id': self.to_location_id,
            'reference_type': self.reference_type,
            'reference_id': self.reference_id,
            'notes': self.notes,
            'performed_by': self.performed_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<InventoryMovement {self.movement_type} prod={self.product_id} qty={self.quantity}>'
