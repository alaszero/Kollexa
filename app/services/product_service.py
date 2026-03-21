"""Servicio de productos."""
from sqlalchemy import func
from app.extensions import db
from app.models.product import Product
from app.models.sale import Sale, SaleDetail
from app.utils.audit import log_action


# Categorías predefinidas del sistema
PRODUCT_CATEGORIES = [
    'Cocina',
    'Electrodomesticos',
    'Hogar',
    'Limpieza',
    'Cuidado Personal',
    'Ropa de Cama',
    'Herramientas',
    'Tecnologia',
    'Otros',
]


def create_product(data, user_id=None):
    """Crear un nuevo producto."""
    product = Product(
        sku=data.get('sku'),
        name=data['name'],
        description=data.get('description'),
        base_price=data['base_price'],
        sell_price=data['sell_price'],
        category=data.get('category'),
    )
    db.session.add(product)
    db.session.flush()

    log_action(
        'product.create',
        entity_type='product',
        entity_id=product.id,
        new_values=product.to_dict(),
        user_id=user_id,
    )
    db.session.commit()
    return product


def update_product(product, data, user_id=None):
    """Actualizar un producto existente."""
    old_values = product.to_dict()
    allowed = ('sku', 'name', 'description', 'base_price', 'sell_price', 'category')

    for field in allowed:
        if field in data:
            setattr(product, field, data[field])

    log_action(
        'product.update',
        entity_type='product',
        entity_id=product.id,
        old_values=old_values,
        new_values=product.to_dict(),
        user_id=user_id,
    )
    db.session.commit()
    return product


def toggle_product(product, user_id=None):
    """Activar/desactivar un producto."""
    product.is_active = not product.is_active

    log_action(
        'product.toggle',
        entity_type='product',
        entity_id=product.id,
        new_values={'is_active': product.is_active},
        user_id=user_id,
    )
    db.session.commit()
    return product


def get_product_by_id(product_id):
    return db.session.get(Product, product_id)


def get_products_query(search=None, category=None, active_only=True):
    """Construir query filtrado de productos."""
    query = Product.query

    if active_only:
        query = query.filter_by(is_active=True)

    if search:
        like = f'%{search}%'
        query = query.filter(
            db.or_(
                Product.name.ilike(like),
                Product.sku.ilike(like),
                Product.description.ilike(like),
            )
        )

    if category:
        query = query.filter_by(category=category)

    return query.order_by(Product.name)


def get_categories():
    """Obtener lista de categorías predefinidas."""
    return PRODUCT_CATEGORIES


def get_units_sold(product_ids=None):
    """Obtener unidades vendidas por producto.

    Args:
        product_ids: Lista de IDs (None = todos)

    Returns:
        Dict {product_id: units_sold}
    """
    query = db.session.query(
        SaleDetail.product_id,
        func.coalesce(func.sum(SaleDetail.quantity), 0).label('units')
    ).join(Sale, SaleDetail.sale_id == Sale.id).filter(
        Sale.status.in_(['active', 'completed']),
    )

    if product_ids:
        query = query.filter(SaleDetail.product_id.in_(product_ids))

    results = query.group_by(SaleDetail.product_id).all()
    return {r[0]: int(r[1]) for r in results}


def get_product_stock(product_ids=None):
    """Obtener stock total por producto (todas las ubicaciones).

    Args:
        product_ids: Lista de IDs (None = todos)

    Returns:
        Dict {product_id: total_stock}
    """
    from app.models.inventory import StockItem
    query = db.session.query(
        StockItem.product_id,
        func.coalesce(func.sum(StockItem.quantity), 0).label('stock')
    )
    if product_ids:
        query = query.filter(StockItem.product_id.in_(product_ids))
    results = query.group_by(StockItem.product_id).all()
    return {r[0]: int(r[1]) for r in results}
