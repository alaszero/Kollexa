"""Servicio de dashboard: queries agregadas para KPIs y resúmenes."""
from datetime import date
from decimal import Decimal
from sqlalchemy import func
from app.extensions import db
from app.models.sale import Sale, SaleDetail
from app.models.payment import PaymentPlan, PaymentInstallment, Payment
from app.models.product import Product
from app.models.customer import Customer
from app.models.user import User
from app.models.inventory import StockItem, StockLocation


def get_dashboard_data(user=None):
    """Obtener todos los datos del dashboard.

    Args:
        user: Usuario actual (para filtrar por agente si aplica)

    Returns:
        Dict con KPIs, tops y resúmenes
    """
    today = date.today()
    is_agent = any(r.name == 'agent' for r in user.roles) if user else False

    data = {
        'kpis': _get_kpis(today, user_id=user.id if is_agent else None),
        'top_products': _get_top_products(user_id=user.id if is_agent else None),
        'recent_payments': _get_recent_payments(user_id=user.id if is_agent else None),
        'agents_summary': [] if is_agent else _get_agents_summary(today),
        'is_agent': is_agent,
    }
    return data


def _get_kpis(today, user_id=None):
    """KPIs principales."""
    # Ventas activas
    active_q = Sale.query.filter_by(status='active')
    if user_id:
        active_q = active_q.filter_by(agent_id=user_id)
    active_sales = active_q.count()

    # Ventas completadas
    completed_q = Sale.query.filter_by(status='completed')
    if user_id:
        completed_q = completed_q.filter_by(agent_id=user_id)
    completed_sales = completed_q.count()

    # Total vendido (ventas activas + completadas)
    total_sold_q = db.session.query(
        func.coalesce(func.sum(Sale.total), 0)
    ).filter(Sale.status.in_(['active', 'completed']))
    if user_id:
        total_sold_q = total_sold_q.filter(Sale.agent_id == user_id)
    total_sold = total_sold_q.scalar()

    # Cobrado hoy
    collected_today_q = db.session.query(
        func.coalesce(func.sum(Payment.amount), 0)
    ).filter(func.date(Payment.payment_date) == today)
    if user_id:
        collected_today_q = collected_today_q.filter(Payment.collected_by == user_id)
    collected_today = collected_today_q.scalar()

    # Total cobrado historico
    total_collected_q = db.session.query(
        func.coalesce(func.sum(Payment.amount), 0)
    )
    if user_id:
        total_collected_q = total_collected_q.filter(Payment.collected_by == user_id)
    total_collected = total_collected_q.scalar()

    # Pendiente total
    pending_q = db.session.query(
        func.coalesce(func.sum(
            PaymentInstallment.expected_amount
            + PaymentInstallment.penalty_amount
            - PaymentInstallment.paid_amount
        ), 0)
    ).join(PaymentPlan).join(
        Sale, PaymentPlan.sale_id == Sale.id
    ).filter(
        PaymentInstallment.status.in_(['pending', 'partial', 'overdue', 'grace']),
        PaymentPlan.status == 'active',
        Sale.status == 'active',
    )
    if user_id:
        pending_q = pending_q.filter(Sale.agent_id == user_id)
    pending_total = pending_q.scalar()

    # Cuotas atrasadas
    overdue_q = PaymentInstallment.query.join(PaymentPlan).join(
        Sale, PaymentPlan.sale_id == Sale.id
    ).filter(
        PaymentInstallment.status == 'overdue',
        PaymentPlan.status == 'active',
        Sale.status == 'active',
    )
    if user_id:
        overdue_q = overdue_q.filter(Sale.agent_id == user_id)
    overdue_count = overdue_q.count()

    # Clientes activos
    customers_q = Customer.query.filter_by(is_active=True)
    if user_id:
        customers_q = customers_q.filter_by(assigned_agent_id=user_id)
    total_customers = customers_q.count()

    return {
        'active_sales': active_sales,
        'completed_sales': completed_sales,
        'total_sold': total_sold,
        'collected_today': collected_today,
        'total_collected': total_collected,
        'pending_total': pending_total,
        'overdue_count': overdue_count,
        'total_customers': total_customers,
    }


def _get_top_products(limit=5, user_id=None):
    """Top productos más vendidos por unidades."""
    query = db.session.query(
        Product.name,
        Product.sku,
        func.sum(SaleDetail.quantity).label('units_sold'),
        func.sum(SaleDetail.line_total).label('revenue'),
    ).join(
        SaleDetail, SaleDetail.product_id == Product.id
    ).join(
        Sale, SaleDetail.sale_id == Sale.id
    ).filter(
        Sale.status.in_(['active', 'completed']),
    )

    if user_id:
        query = query.filter(Sale.agent_id == user_id)

    return query.group_by(
        Product.id, Product.name, Product.sku
    ).order_by(
        func.sum(SaleDetail.quantity).desc()
    ).limit(limit).all()


def _get_recent_payments(limit=10, user_id=None):
    """Últimos pagos registrados."""
    query = Payment.query
    if user_id:
        query = query.filter_by(collected_by=user_id)
    return query.order_by(Payment.created_at.desc()).limit(limit).all()


def _get_agents_summary(today):
    """Resumen por agente: ventas activas, cobrado hoy, stock."""
    from app.models.user import Role
    agent_users = User.query.filter(
        User.roles.any(Role.name == 'agent'),
    ).all()
    # Filter active in Python (is_active from UserMixin property)
    agent_users = [u for u in agent_users if u.is_active]

    summary = []
    for agent in agent_users:
        active = Sale.query.filter_by(agent_id=agent.id, status='active').count()

        collected = db.session.query(
            func.coalesce(func.sum(Payment.amount), 0)
        ).filter(
            Payment.collected_by == agent.id,
            func.date(Payment.payment_date) == today,
        ).scalar()

        # Stock items count
        location = StockLocation.query.filter_by(
            user_id=agent.id, type='agent'
        ).first()
        stock_items = 0
        if location:
            stock_items = db.session.query(
                func.coalesce(func.sum(StockItem.quantity), 0)
            ).filter_by(location_id=location.id).scalar()

        summary.append({
            'agent': agent,
            'active_sales': active,
            'collected_today': collected,
            'stock_items': stock_items,
        })

    return summary
