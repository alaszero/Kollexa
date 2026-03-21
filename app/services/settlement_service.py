"""Servicio de liquidaciones: control de dinero en transito."""
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import func
from app.extensions import db
from app.models.settlement import AgentSettlement, SettlementDetail
from app.models.payment import Payment, PaymentInstallment, PaymentPlan
from app.models.sale import Sale
from app.models.user import User, Role
from app.utils.audit import log_action


class SettlementError(Exception):
    pass


def get_unsettled_payments(agent_id):
    """Obtener pagos cobrados por un agente que no estan en ninguna liquidacion.

    Returns:
        Lista de Payment objects
    """
    # Subquery: payment_ids que ya estan en un settlement
    settled_ids = db.session.query(
        SettlementDetail.payment_id
    ).subquery()

    payments = Payment.query.filter(
        Payment.collected_by == agent_id,
        ~Payment.id.in_(db.session.query(settled_ids.c.payment_id)),
    ).order_by(Payment.payment_date).all()

    return payments


def get_unsettled_total(agent_id):
    """Obtener el total no liquidado de un agente."""
    settled_ids = db.session.query(
        SettlementDetail.payment_id
    ).subquery()

    total = db.session.query(
        func.coalesce(func.sum(Payment.amount), 0)
    ).filter(
        Payment.collected_by == agent_id,
        ~Payment.id.in_(db.session.query(settled_ids.c.payment_id)),
    ).scalar()

    return total


def create_settlement(agent_id, created_by):
    """Crear una liquidacion con todos los pagos no liquidados del agente.

    Returns:
        AgentSettlement or None if no payments
    """
    payments = get_unsettled_payments(agent_id)
    if not payments:
        return None

    total = sum(p.amount for p in payments)

    settlement = AgentSettlement(
        agent_id=agent_id,
        total_amount=total,
        payment_count=len(payments),
        status='pending',
    )
    db.session.add(settlement)
    db.session.flush()

    for p in payments:
        detail = SettlementDetail(
            settlement_id=settlement.id,
            payment_id=p.id,
        )
        db.session.add(detail)

    log_action(
        'settlement.create',
        entity_type='settlement',
        entity_id=settlement.id,
        new_values={
            'agent_id': agent_id,
            'total': str(total),
            'payments': len(payments),
        },
        user_id=created_by,
    )
    db.session.commit()
    return settlement


def confirm_settlement(settlement_id, confirmed_by):
    """Confirmar que el dinero de una liquidacion fue recibido.

    Args:
        settlement_id: ID de la liquidacion
        confirmed_by: ID del usuario que confirma (admin)
    """
    settlement = db.session.get(AgentSettlement, settlement_id)
    if not settlement:
        raise SettlementError('Liquidacion no encontrada.')

    if settlement.status == 'confirmed':
        raise SettlementError('Esta liquidacion ya fue confirmada.')

    settlement.status = 'confirmed'
    settlement.confirmed_at = datetime.now(timezone.utc)
    settlement.confirmed_by = confirmed_by

    log_action(
        'settlement.confirm',
        entity_type='settlement',
        entity_id=settlement.id,
        new_values={
            'confirmed_by': confirmed_by,
            'total': str(settlement.total_amount),
        },
        user_id=confirmed_by,
    )
    db.session.commit()
    return settlement


def get_settlement_by_id(settlement_id):
    return db.session.get(AgentSettlement, settlement_id)


def get_settlements_query(agent_id=None, status=None):
    """Query filtrado de liquidaciones."""
    query = AgentSettlement.query
    if agent_id:
        query = query.filter_by(agent_id=agent_id)
    if status:
        query = query.filter_by(status=status)
    return query.order_by(AgentSettlement.created_at.desc())


def get_agents_settlement_summary():
    """Resumen de liquidaciones por agente: total no liquidado."""
    from app.models.user import Role
    agent_users = User.query.filter(
        User.roles.any(Role.name == 'agent'),
    ).all()
    agent_users = [u for u in agent_users if u.is_active]

    summary = []
    for agent in agent_users:
        unsettled = get_unsettled_total(agent.id)
        pending_settlements = AgentSettlement.query.filter_by(
            agent_id=agent.id, status='pending'
        ).count()

        summary.append({
            'agent': agent,
            'unsettled_amount': unsettled,
            'pending_settlements': pending_settlements,
        })

    return summary
