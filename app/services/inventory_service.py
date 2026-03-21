"""Servicio de inventario: surtido, devolución, compra, conciliación."""
from datetime import datetime, timezone
from app.extensions import db
from app.models.inventory import StockLocation, StockItem, InventoryMovement
from app.models.product import Product
from app.utils.audit import log_action


class InsufficientStockError(Exception):
    """No hay suficiente stock en la ubicación."""
    pass


class InvalidMovementError(Exception):
    """Movimiento de inventario inválido."""
    pass


# ──────────────────────────────────────────────
# Helpers internos
# ──────────────────────────────────────────────

def _get_or_create_stock_item(location_id, product_id):
    """Obtener o crear StockItem para una ubicación+producto."""
    item = StockItem.query.filter_by(
        location_id=location_id,
        product_id=product_id,
    ).first()

    if not item:
        item = StockItem(
            location_id=location_id,
            product_id=product_id,
            quantity=0,
        )
        db.session.add(item)
        db.session.flush()

    return item


def _create_movement(product_id, quantity, movement_type,
                     from_location_id=None, to_location_id=None,
                     reference_type=None, reference_id=None,
                     notes=None, performed_by=None):
    """Registrar un movimiento en el journal."""
    movement = InventoryMovement(
        product_id=product_id,
        quantity=quantity,
        movement_type=movement_type,
        from_location_id=from_location_id,
        to_location_id=to_location_id,
        reference_type=reference_type,
        reference_id=reference_id,
        notes=notes,
        performed_by=performed_by,
    )
    db.session.add(movement)
    return movement


# ──────────────────────────────────────────────
# Operaciones de inventario
# ──────────────────────────────────────────────

def purchase_stock(product_id, quantity, warehouse_id, performed_by, notes=None):
    """Registrar compra/entrada de mercancía al almacén.

    Args:
        product_id: ID del producto
        quantity: Cantidad (debe ser > 0)
        warehouse_id: ID del StockLocation tipo warehouse
        performed_by: ID del usuario que realiza la operación
        notes: Notas opcionales
    """
    if quantity <= 0:
        raise InvalidMovementError('La cantidad debe ser mayor a cero.')

    item = _get_or_create_stock_item(warehouse_id, product_id)
    item.quantity += quantity

    _create_movement(
        product_id=product_id,
        quantity=quantity,
        movement_type='purchase',
        to_location_id=warehouse_id,
        reference_type='manual',
        notes=notes,
        performed_by=performed_by,
    )

    log_action(
        'inventory.purchase',
        entity_type='product',
        entity_id=product_id,
        new_values={'quantity': quantity, 'warehouse_id': warehouse_id},
        user_id=performed_by,
    )
    db.session.commit()
    return item


def dispatch_to_agent(product_id, quantity, warehouse_id, agent_location_id, performed_by, notes=None):
    """Surtir agente: mover producto de almacén a agente.

    Args:
        product_id: ID del producto
        quantity: Cantidad a despachar
        warehouse_id: ID del StockLocation del almacén
        agent_location_id: ID del StockLocation del agente
        performed_by: ID del usuario
    """
    if quantity <= 0:
        raise InvalidMovementError('La cantidad debe ser mayor a cero.')

    # Verificar stock en almacén
    warehouse_item = _get_or_create_stock_item(warehouse_id, product_id)
    if warehouse_item.quantity < quantity:
        raise InsufficientStockError(
            f'Stock insuficiente en almacén. Disponible: {warehouse_item.quantity}, solicitado: {quantity}'
        )

    # Mover
    warehouse_item.quantity -= quantity
    agent_item = _get_or_create_stock_item(agent_location_id, product_id)
    agent_item.quantity += quantity

    _create_movement(
        product_id=product_id,
        quantity=quantity,
        movement_type='dispatch',
        from_location_id=warehouse_id,
        to_location_id=agent_location_id,
        reference_type='manual',
        notes=notes,
        performed_by=performed_by,
    )

    log_action(
        'inventory.dispatch',
        entity_type='product',
        entity_id=product_id,
        new_values={
            'quantity': quantity,
            'from': warehouse_id,
            'to': agent_location_id,
        },
        user_id=performed_by,
    )
    db.session.commit()
    return agent_item


def return_to_warehouse(product_id, quantity, agent_location_id, warehouse_id, performed_by, notes=None):
    """Agente devuelve producto al almacén."""
    if quantity <= 0:
        raise InvalidMovementError('La cantidad debe ser mayor a cero.')

    agent_item = _get_or_create_stock_item(agent_location_id, product_id)
    if agent_item.quantity < quantity:
        raise InsufficientStockError(
            f'El agente no tiene suficiente stock. Tiene: {agent_item.quantity}, devuelve: {quantity}'
        )

    agent_item.quantity -= quantity
    warehouse_item = _get_or_create_stock_item(warehouse_id, product_id)
    warehouse_item.quantity += quantity

    _create_movement(
        product_id=product_id,
        quantity=quantity,
        movement_type='return_to_warehouse',
        from_location_id=agent_location_id,
        to_location_id=warehouse_id,
        reference_type='manual',
        notes=notes,
        performed_by=performed_by,
    )

    log_action(
        'inventory.return',
        entity_type='product',
        entity_id=product_id,
        new_values={
            'quantity': quantity,
            'from_agent': agent_location_id,
            'to_warehouse': warehouse_id,
        },
        user_id=performed_by,
    )
    db.session.commit()
    return warehouse_item


def adjust_stock(product_id, location_id, new_quantity, performed_by, notes=None):
    """Ajuste de inventario (conteo físico)."""
    item = _get_or_create_stock_item(location_id, product_id)
    old_qty = item.quantity
    diff = new_quantity - old_qty

    if diff == 0:
        return item  # No hay cambio

    item.quantity = new_quantity

    movement_type = 'adjustment_in' if diff > 0 else 'adjustment_out'
    _create_movement(
        product_id=product_id,
        quantity=abs(diff),
        movement_type=movement_type,
        from_location_id=location_id if diff < 0 else None,
        to_location_id=location_id if diff > 0 else None,
        reference_type='manual',
        notes=notes or f'Ajuste: {old_qty} → {new_quantity}',
        performed_by=performed_by,
    )

    log_action(
        'inventory.adjust',
        entity_type='stock_item',
        entity_id=item.id,
        old_values={'quantity': old_qty},
        new_values={'quantity': new_quantity},
        user_id=performed_by,
    )
    db.session.commit()
    return item


def batch_purchase(items, warehouse_id, performed_by, notes=None):
    """Registrar compra multiple de productos.

    Args:
        items: Lista de dicts [{product_id, quantity}, ...]
        warehouse_id: ID del almacen
        performed_by: ID del usuario
        notes: Notas opcionales
    Returns:
        Numero de items procesados
    """
    count = 0
    for entry in items:
        pid = entry.get('product_id')
        qty = entry.get('quantity', 0)
        if not pid or qty <= 0:
            continue

        item = _get_or_create_stock_item(warehouse_id, pid)
        item.quantity += qty

        _create_movement(
            product_id=pid, quantity=qty,
            movement_type='purchase',
            to_location_id=warehouse_id,
            reference_type='manual',
            notes=notes,
            performed_by=performed_by,
        )
        count += 1

    if count > 0:
        log_action(
            'inventory.batch_purchase',
            entity_type='warehouse',
            entity_id=warehouse_id,
            new_values={'items': len(items), 'processed': count},
            user_id=performed_by,
        )
        db.session.commit()
    return count


def batch_dispatch(items, warehouse_id, agent_location_id, performed_by, notes=None):
    """Surtir agente con multiples productos.

    Args:
        items: Lista de dicts [{product_id, quantity}, ...]
    Raises:
        InsufficientStockError si algun producto no tiene stock
    """
    # Validar todo antes de aplicar
    for entry in items:
        pid = entry.get('product_id')
        qty = entry.get('quantity', 0)
        if not pid or qty <= 0:
            continue
        wh_item = _get_or_create_stock_item(warehouse_id, pid)
        if wh_item.quantity < qty:
            product = Product.query.get(pid)
            raise InsufficientStockError(
                f'Stock insuficiente de "{product.name}". '
                f'Disponible: {wh_item.quantity}, solicitado: {qty}'
            )

    count = 0
    for entry in items:
        pid = entry.get('product_id')
        qty = entry.get('quantity', 0)
        if not pid or qty <= 0:
            continue

        wh_item = _get_or_create_stock_item(warehouse_id, pid)
        wh_item.quantity -= qty

        agent_item = _get_or_create_stock_item(agent_location_id, pid)
        agent_item.quantity += qty

        _create_movement(
            product_id=pid, quantity=qty,
            movement_type='dispatch',
            from_location_id=warehouse_id,
            to_location_id=agent_location_id,
            reference_type='manual',
            notes=notes,
            performed_by=performed_by,
        )
        count += 1

    if count > 0:
        log_action(
            'inventory.batch_dispatch',
            entity_type='warehouse',
            entity_id=warehouse_id,
            new_values={'agent_location': agent_location_id, 'items': count},
            user_id=performed_by,
        )
        db.session.commit()
    return count


def batch_return(items, agent_location_id, warehouse_id, performed_by, notes=None):
    """Devolucion multiple de agente a almacen.

    Args:
        items: Lista de dicts [{product_id, quantity}, ...]
    Raises:
        InsufficientStockError si el agente no tiene suficiente
    """
    for entry in items:
        pid = entry.get('product_id')
        qty = entry.get('quantity', 0)
        if not pid or qty <= 0:
            continue
        agent_item = _get_or_create_stock_item(agent_location_id, pid)
        if agent_item.quantity < qty:
            product = Product.query.get(pid)
            raise InsufficientStockError(
                f'El agente no tiene suficiente "{product.name}". '
                f'Tiene: {agent_item.quantity}, devuelve: {qty}'
            )

    count = 0
    for entry in items:
        pid = entry.get('product_id')
        qty = entry.get('quantity', 0)
        if not pid or qty <= 0:
            continue

        agent_item = _get_or_create_stock_item(agent_location_id, pid)
        agent_item.quantity -= qty

        wh_item = _get_or_create_stock_item(warehouse_id, pid)
        wh_item.quantity += qty

        _create_movement(
            product_id=pid, quantity=qty,
            movement_type='return_to_warehouse',
            from_location_id=agent_location_id,
            to_location_id=warehouse_id,
            reference_type='manual',
            notes=notes,
            performed_by=performed_by,
        )
        count += 1

    if count > 0:
        log_action(
            'inventory.batch_return',
            entity_type='warehouse',
            entity_id=warehouse_id,
            new_values={'agent_location': agent_location_id, 'items': count},
            user_id=performed_by,
        )
        db.session.commit()
    return count


def deduct_for_sale(product_id, quantity, agent_location_id, sale_id, performed_by):
    """Descontar stock del agente por una venta. Llamado desde sale_service."""
    agent_item = _get_or_create_stock_item(agent_location_id, product_id)
    if agent_item.quantity < quantity:
        raise InsufficientStockError(
            f'Stock insuficiente del agente. Tiene: {agent_item.quantity}, venta: {quantity}'
        )

    agent_item.quantity -= quantity

    _create_movement(
        product_id=product_id,
        quantity=quantity,
        movement_type='sale',
        from_location_id=agent_location_id,
        reference_type='sale',
        reference_id=sale_id,
        performed_by=performed_by,
    )
    # No commit aquí — se hace en la transacción de venta
    return agent_item


# ──────────────────────────────────────────────
# Consultas
# ──────────────────────────────────────────────

def get_warehouse():
    """Obtener el almacén principal."""
    return StockLocation.query.filter_by(type='warehouse', is_active=True).first()


def get_agent_location(user_id):
    """Obtener la ubicación de stock de un agente."""
    return StockLocation.query.filter_by(type='agent', user_id=user_id, is_active=True).first()


def get_stock_by_location(location_id):
    """Obtener todo el stock de una ubicación con datos de producto."""
    return db.session.query(
        StockItem, Product
    ).join(
        Product, StockItem.product_id == Product.id
    ).filter(
        StockItem.location_id == location_id,
        StockItem.quantity > 0,
        Product.is_active == True,
    ).order_by(Product.name).all()


def get_global_stock():
    """Stock global: por producto, sumado de todas las ubicaciones."""
    results = db.session.query(
        Product.id,
        Product.name,
        Product.sku,
        StockLocation.type,
        StockLocation.name.label('location_name'),
        StockItem.quantity,
    ).join(
        StockItem, Product.id == StockItem.product_id
    ).join(
        StockLocation, StockItem.location_id == StockLocation.id
    ).filter(
        StockItem.quantity > 0,
        Product.is_active == True,
    ).order_by(Product.name, StockLocation.type).all()

    return results


def get_agents_stock_summary():
    """Resumen de stock por agente (para dashboard admin)."""
    from app.models.user import User

    results = db.session.query(
        User.id,
        User.full_name,
        StockLocation.id.label('location_id'),
        db.func.sum(StockItem.quantity).label('total_items'),
        db.func.count(StockItem.product_id).label('product_count'),
    ).join(
        StockLocation, StockLocation.user_id == User.id
    ).join(
        StockItem, StockItem.location_id == StockLocation.id
    ).filter(
        StockLocation.type == 'agent',
        StockItem.quantity > 0,
    ).group_by(
        User.id, User.full_name, StockLocation.id,
    ).all()

    return results


def get_movements_query(product_id=None, location_id=None,
                        movement_type=None, agent_user_id=None):
    """Construir query filtrado de movimientos."""
    query = InventoryMovement.query

    if product_id:
        query = query.filter_by(product_id=product_id)

    if movement_type:
        query = query.filter_by(movement_type=movement_type)

    if location_id:
        query = query.filter(
            db.or_(
                InventoryMovement.from_location_id == location_id,
                InventoryMovement.to_location_id == location_id,
            )
        )

    if agent_user_id:
        agent_loc = get_agent_location(agent_user_id)
        if agent_loc:
            query = query.filter(
                db.or_(
                    InventoryMovement.from_location_id == agent_loc.id,
                    InventoryMovement.to_location_id == agent_loc.id,
                )
            )

    return query.order_by(InventoryMovement.created_at.desc())


def get_reconciliation(location_id=None):
    """Datos de conciliación de inventario."""
    from sqlalchemy import func

    # Total compras
    purchases = db.session.query(
        func.coalesce(func.sum(InventoryMovement.quantity), 0)
    ).filter_by(movement_type='purchase').scalar()

    # Total ventas
    sales = db.session.query(
        func.coalesce(func.sum(InventoryMovement.quantity), 0)
    ).filter(InventoryMovement.movement_type.in_(['sale', 'sale_direct'])).scalar()

    # Total ajustes negativos (merma)
    shrinkage = db.session.query(
        func.coalesce(func.sum(InventoryMovement.quantity), 0)
    ).filter_by(movement_type='adjustment_out').scalar()

    # Stock actual total
    current_stock = db.session.query(
        func.coalesce(func.sum(StockItem.quantity), 0)
    ).scalar()

    return {
        'total_purchases': int(purchases),
        'total_sales': int(sales),
        'total_shrinkage': int(shrinkage),
        'current_stock': int(current_stock),
        'expected_stock': int(purchases) - int(sales) - int(shrinkage),
        'difference': int(current_stock) - (int(purchases) - int(sales) - int(shrinkage)),
    }
