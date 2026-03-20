"""Servicio de ventas con generación automática de plan de pagos."""
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from app.extensions import db
from app.models.sale import Sale, SaleDetail
from app.models.payment import PaymentPlan, PaymentInstallment
from app.models.product import Product
from app.services import inventory_service as inv
from app.services.config_service import (
    is_interest_enabled, get_default_interest_rate, get_default_grace_days,
)
from app.utils.audit import log_action
from app.utils.helpers import round_currency


class SaleValidationError(Exception):
    pass


def create_sale(data, agent_id):
    """Crear una venta completa: sale + detalles + plan de pagos + descuento de inventario.

    Args:
        data: {
            'customer_id': int,
            'items': [{'product_id': int, 'quantity': int, 'unit_price': Decimal (opcional)}],
            'num_installments': int,
            'interest_rate': Decimal (opcional, override de config),
            'start_date': date (opcional, default hoy + 7 dias),
            'frequency_days': int (opcional, default 7),
            'notes': str (opcional),
        }
        agent_id: ID del agente que realiza la venta

    Returns:
        Sale creada
    """
    # ── Validaciones ──────────────────────────────
    customer_id = data.get('customer_id')
    items = data.get('items', [])
    num_installments = int(data.get('num_installments', 10))

    if not customer_id:
        raise SaleValidationError('Cliente es requerido.')
    if not items:
        raise SaleValidationError('La venta debe tener al menos un producto.')
    if num_installments < 1:
        raise SaleValidationError('El número de cuotas debe ser al menos 1.')

    # Obtener ubicación del agente
    agent_location = inv.get_agent_location(agent_id)
    if not agent_location:
        raise SaleValidationError('El agente no tiene ubicación de inventario asignada.')

    # ── Calcular subtotal ─────────────────────────
    sale_details = []
    subtotal = Decimal('0')

    for item_data in items:
        product_id = int(item_data['product_id'])
        quantity = int(item_data['quantity'])

        if quantity <= 0:
            raise SaleValidationError(f'Cantidad inválida para producto {product_id}.')

        product = db.session.get(Product, product_id)
        if not product or not product.is_active:
            raise SaleValidationError(f'Producto {product_id} no encontrado o inactivo.')

        # Precio: usar override si se da, sino precio de catálogo
        unit_price = Decimal(str(item_data.get('unit_price', product.sell_price)))
        line_total = round_currency(unit_price * quantity)

        sale_details.append({
            'product_id': product_id,
            'quantity': quantity,
            'unit_price': unit_price,
            'line_total': line_total,
        })
        subtotal += line_total

    # ── Calcular interés ──────────────────────────
    interest_rate = Decimal('0')
    interest_total = Decimal('0')

    if is_interest_enabled():
        interest_rate = Decimal(str(
            data.get('interest_rate', get_default_interest_rate())
        ))
        if interest_rate > 0:
            interest_total = round_currency(subtotal * interest_rate / 100)

    total = subtotal + interest_total

    # ── Crear la venta ────────────────────────────
    sale_date = date.today()
    sale = Sale(
        customer_id=customer_id,
        agent_id=agent_id,
        stock_location_id=agent_location.id,
        sale_date=sale_date,
        subtotal=subtotal,
        interest_total=interest_total,
        total=total,
        num_installments=num_installments,
        status='active',
        notes=data.get('notes'),
    )
    db.session.add(sale)
    db.session.flush()  # Obtener sale.id

    # ── Crear detalles de venta ───────────────────
    for detail_data in sale_details:
        detail = SaleDetail(
            sale_id=sale.id,
            product_id=detail_data['product_id'],
            quantity=detail_data['quantity'],
            unit_price=detail_data['unit_price'],
            line_total=detail_data['line_total'],
        )
        db.session.add(detail)

    # ── Descontar inventario del agente ───────────
    for detail_data in sale_details:
        inv.deduct_for_sale(
            product_id=detail_data['product_id'],
            quantity=detail_data['quantity'],
            agent_location_id=agent_location.id,
            sale_id=sale.id,
            performed_by=agent_id,
        )

    # ── Generar plan de pagos ─────────────────────
    frequency_days = int(data.get('frequency_days', 7))
    start_date = data.get('start_date')
    if isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)
    if not start_date:
        start_date = sale_date + timedelta(days=frequency_days)

    grace_days = int(data.get('grace_days', get_default_grace_days()))

    plan = _generate_payment_plan(
        sale=sale,
        total=total,
        num_installments=num_installments,
        start_date=start_date,
        frequency_days=frequency_days,
        interest_rate=interest_rate,
        grace_days=grace_days,
    )

    # ── Auditoría ─────────────────────────────────
    log_action(
        'sale.create',
        entity_type='sale',
        entity_id=sale.id,
        new_values={
            'customer_id': customer_id,
            'total': str(total),
            'num_installments': num_installments,
            'items_count': len(items),
        },
        user_id=agent_id,
    )

    db.session.commit()
    return sale


def _generate_payment_plan(sale, total, num_installments, start_date,
                           frequency_days, interest_rate, grace_days):
    """Generar plan de pagos con cuotas iguales (última ajustada por redondeo)."""
    installment_amount = round_currency(total / num_installments)

    plan = PaymentPlan(
        sale_id=sale.id,
        total_amount=total,
        num_installments=num_installments,
        installment_amount=installment_amount,
        interest_rate=interest_rate,
        penalty_rate=Decimal('0'),  # Se aplica dinámicamente en cobranza
        grace_days=grace_days,
        start_date=start_date,
        frequency_days=frequency_days,
        status='active',
    )
    db.session.add(plan)
    db.session.flush()

    # Generar cuotas
    accumulated = Decimal('0')
    for i in range(1, num_installments + 1):
        due_date = start_date + timedelta(days=frequency_days * (i - 1))

        if i < num_installments:
            amount = installment_amount
        else:
            # Última cuota absorbe el redondeo
            amount = total - accumulated

        installment = PaymentInstallment(
            plan_id=plan.id,
            installment_num=i,
            due_date=due_date,
            expected_amount=amount,
            paid_amount=Decimal('0'),
            penalty_amount=Decimal('0'),
            status='pending',
        )
        db.session.add(installment)
        accumulated += amount

    return plan


def get_sale_by_id(sale_id):
    return db.session.get(Sale, sale_id)


def get_sale_full(sale_id):
    """Obtener venta con detalles, plan de pagos y cuotas."""
    sale = db.session.get(Sale, sale_id)
    if not sale:
        return None
    return sale


def get_sales_query(customer_id=None, agent_id=None, status=None):
    """Query filtrado de ventas."""
    query = Sale.query

    if customer_id:
        query = query.filter_by(customer_id=customer_id)

    if agent_id:
        query = query.filter_by(agent_id=agent_id)

    if status:
        query = query.filter_by(status=status)

    return query.order_by(Sale.created_at.desc())


def cancel_sale(sale, user_id=None):
    """Cancelar una venta (no devuelve inventario automáticamente)."""
    if sale.status == 'cancelled':
        raise SaleValidationError('La venta ya está cancelada.')

    old_status = sale.status
    sale.status = 'cancelled'

    # Cancelar plan de pagos
    if sale.payment_plan:
        sale.payment_plan.status = 'cancelled'
        for inst in sale.payment_plan.installments:
            if inst.status == 'pending':
                inst.status = 'cancelled'

    log_action(
        'sale.cancel',
        entity_type='sale',
        entity_id=sale.id,
        old_values={'status': old_status},
        new_values={'status': 'cancelled'},
        user_id=user_id,
    )
    db.session.commit()
    return sale


def get_sale_summary(sale):
    """Resumen de una venta para mostrar en UI."""
    plan = sale.payment_plan
    if not plan:
        return {'paid': Decimal('0'), 'remaining': sale.total, 'progress': 0, 'installments_paid': 0}

    paid = sum(inst.paid_amount for inst in plan.installments)
    remaining = sale.total - paid
    progress = int((paid / sale.total * 100)) if sale.total > 0 else 0
    installments_paid = sum(1 for inst in plan.installments if inst.status == 'paid')

    return {
        'paid': paid,
        'remaining': remaining,
        'progress': progress,
        'installments_paid': installments_paid,
        'total_installments': plan.num_installments,
    }
