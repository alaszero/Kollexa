"""Servicio del portal de clientes."""
from datetime import datetime, timezone, timedelta
from app.extensions import db
from app.models.customer import Customer, CustomerPortalToken
from app.models.sale import Sale
from app.models.payment import PaymentPlan, PaymentInstallment
from app.utils.audit import log_action


def generate_portal_token(customer_id, sale_id=None, expires_days=90, user_id=None):
    """Generar un token de acceso al portal para un cliente.

    Args:
        customer_id: ID del cliente
        sale_id: ID de la venta (None = acceso a todas las ventas del cliente)
        expires_days: Días hasta expiración (None = sin expiración)
        user_id: Quién genera el token

    Returns:
        CustomerPortalToken
    """
    token_str = CustomerPortalToken.generate_token()
    expires_at = None
    if expires_days:
        expires_at = datetime.utcnow() + timedelta(days=expires_days)

    token = CustomerPortalToken(
        customer_id=customer_id,
        token=token_str,
        sale_id=sale_id,
        is_active=True,
        expires_at=expires_at,
    )
    db.session.add(token)

    log_action(
        'portal.token_generated',
        entity_type='customer',
        entity_id=customer_id,
        new_values={'sale_id': sale_id, 'expires_days': expires_days},
        user_id=user_id,
    )
    db.session.commit()
    return token


def get_portal_by_token(token_str):
    """Validar token y obtener datos del portal.

    Returns:
        dict con customer, sales, etc. o None si token inválido
    """
    token = CustomerPortalToken.query.filter_by(token=token_str).first()
    if not token or not token.is_valid:
        return None

    customer = db.session.get(Customer, token.customer_id)
    if not customer:
        return None

    # Obtener ventas
    if token.sale_id:
        # Token específico de una venta
        sales = Sale.query.filter_by(id=token.sale_id, customer_id=customer.id).all()
    else:
        # Token general: todas las ventas activas/completadas
        sales = Sale.query.filter(
            Sale.customer_id == customer.id,
            Sale.status.in_(['active', 'completed']),
        ).order_by(Sale.created_at.desc()).all()

    # Construir resumen por venta
    sales_data = []
    total_debt = 0
    total_paid = 0

    for sale in sales:
        plan = sale.payment_plan
        if not plan:
            continue

        paid = sum(inst.paid_amount for inst in plan.installments)
        remaining = sale.total - paid
        progress = int((paid / sale.total * 100)) if sale.total > 0 else 0
        installments_paid = sum(1 for inst in plan.installments if inst.status == 'paid')

        next_installment = None
        for inst in plan.installments:
            if inst.status in ('pending', 'partial', 'overdue', 'grace'):
                next_installment = inst
                break

        sales_data.append({
            'sale': sale,
            'plan': plan,
            'paid': paid,
            'remaining': remaining,
            'progress': progress,
            'installments_paid': installments_paid,
            'total_installments': plan.num_installments,
            'next_installment': next_installment,
        })

        if sale.status == 'active':
            total_debt += remaining
            total_paid += paid

    return {
        'token': token,
        'customer': customer,
        'sales': sales_data,
        'total_debt': total_debt,
        'total_paid': total_paid,
    }


def revoke_token(token_id, user_id=None):
    """Revocar un token de portal."""
    token = db.session.get(CustomerPortalToken, token_id)
    if token:
        token.is_active = False
        log_action(
            'portal.token_revoked',
            entity_type='customer_portal_token',
            entity_id=token_id,
            user_id=user_id,
        )
        db.session.commit()
    return token


def get_customer_tokens(customer_id):
    """Obtener tokens activos de un cliente."""
    return CustomerPortalToken.query.filter_by(
        customer_id=customer_id,
        is_active=True,
    ).all()
