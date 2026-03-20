"""Servicio de productos."""
from app.extensions import db
from app.models.product import Product
from app.utils.audit import log_action


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
    """Obtener lista de categorías únicas."""
    results = db.session.query(Product.category).filter(
        Product.category.isnot(None),
        Product.is_active == True
    ).distinct().order_by(Product.category).all()
    return [r[0] for r in results if r[0]]
