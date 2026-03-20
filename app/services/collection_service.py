"""Servicio de cobranza: registrar pagos, actualizar cuotas, penalizaciones."""
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from app.extensions import db
from app.models.payment import PaymentPlan, PaymentInstallment, Payment
from app.models.sale import Sale
from app.services.config_service import (
    is_penalty_enabled, get_config,
)
from app.utils.audit import log_action
from app.utils.helpers import round_currency


class CollectionError(Exception):
    pass


# ──────────────────────────────────────────────
# Registrar pago
# ──────────────────────────────────────────────

def collect_payment(installment_id, amount, collected_by,
                    payment_method='cash', notes=None,
                    latitude=None, longitude=None):
    """Registrar un pago sobre una cuota.

    Soporta:
    - Pago exacto → cuota marcada como 'paid'
    - Pago parcial → cuota marcada como 'partial'
    - Sobrepago → excedente se aplica a cuotas siguientes

    Args:
        installment_id: ID de la cuota a pagar
        amount: Monto del pago (Decimal o float)
        collected_by: ID del usuario cobrador
        payment_method: 'cash' o 'transfer'
        notes: Notas opcionales
        latitude/longitude: GPS del cobrador (opcional)

    Returns:
        Lista de Payment creados
    """
    amount = Decimal(str(amount))
    if amount <= 0:
        raise CollectionError('El monto debe ser mayor a cero.')

    installment = db.session.get(PaymentInstallment, installment_id)
    if not installment:
        raise CollectionError('Cuota no encontrada.')

    plan = installment.plan
    if plan.status != 'active':
        raise CollectionError('El plan de pagos no está activo.')

    sale = plan.sale
    if sale.status != 'active':
        raise CollectionError('La venta no está activa.')

    payments_created = []
    remaining_amount = amount

    # Obtener cuotas pendientes desde la actual en adelante
    pending_installments = PaymentInstallment.query.filter(
        PaymentInstallment.plan_id == plan.id,
        PaymentInstallment.installment_num >= installment.installment_num,
        PaymentInstallment.status.in_(['pending', 'partial', 'overdue', 'grace']),
    ).order_by(PaymentInstallment.installment_num).all()

    if not pending_installments:
        raise CollectionError('No hay cuotas pendientes de pago.')

    now = datetime.now(timezone.utc)

    for inst in pending_installments:
        if remaining_amount <= 0:
            break

        owed = inst.expected_amount + inst.penalty_amount - inst.paid_amount
        if owed <= 0:
            continue

        # Monto a aplicar a esta cuota
        apply_amount = min(remaining_amount, owed)

        payment = Payment(
            installment_id=inst.id,
            amount=apply_amount,
            payment_date=now,
            collected_by=collected_by,
            payment_method=payment_method,
            notes=notes if inst.id == installment_id else f'Excedente de cuota #{installment.installment_num}',
            latitude=latitude,
            longitude=longitude,
        )
        db.session.add(payment)
        payments_created.append(payment)

        inst.paid_amount += apply_amount
        remaining_amount -= apply_amount

        # Actualizar status de la cuota
        total_owed = inst.expected_amount + inst.penalty_amount
        if inst.paid_amount >= total_owed:
            inst.status = 'paid'
            inst.paid_at = now
        else:
            inst.status = 'partial'

    # Verificar si la venta se completó
    _check_sale_completion(plan)

    log_action(
        'collection.payment',
        entity_type='payment',
        entity_id=installment_id,
        new_values={
            'amount': str(amount),
            'applied_to': len(payments_created),
            'sale_id': sale.id,
        },
        user_id=collected_by,
    )

    db.session.commit()
    return payments_created


def _check_sale_completion(plan):
    """Verificar si todas las cuotas están pagadas → completar la venta."""
    all_paid = all(
        inst.status == 'paid'
        for inst in plan.installments
    )
    if all_paid:
        plan.status = 'completed'
        plan.sale.status = 'completed'


# ──────────────────────────────────────────────
# Penalizaciones
# ──────────────────────────────────────────────

def apply_penalties_for_date(target_date=None):
    """Aplicar penalizaciones a cuotas vencidas.

    Se ejecuta diariamente (o manualmente). Aplica penalización a cuotas
    cuya fecha de vencimiento + días de gracia haya pasado.

    Returns:
        Número de cuotas penalizadas
    """
    if not is_penalty_enabled():
        return 0

    if target_date is None:
        target_date = date.today()

    penalty_rate = Decimal(str(get_config('default_penalty_rate', 5)))
    if penalty_rate <= 0:
        return 0

    # Buscar cuotas vencidas sin penalizar
    overdue_installments = PaymentInstallment.query.join(
        PaymentPlan
    ).filter(
        PaymentInstallment.status.in_(['pending', 'partial']),
        PaymentInstallment.due_date < target_date,
        PaymentInstallment.penalty_amount == 0,
        PaymentPlan.status == 'active',
    ).all()

    count = 0
    for inst in overdue_installments:
        grace_days = inst.plan.grace_days
        days_overdue = (target_date - inst.due_date).days

        if days_overdue <= grace_days:
            # Aún en período de gracia
            inst.status = 'grace'
            continue

        # Aplicar penalización
        penalty = round_currency(inst.expected_amount * penalty_rate / 100)
        inst.penalty_amount = penalty
        inst.status = 'overdue'
        count += 1

        log_action(
            'collection.penalty',
            entity_type='installment',
            entity_id=inst.id,
            new_values={
                'penalty_amount': str(penalty),
                'days_overdue': days_overdue,
            },
        )

    if count > 0:
        db.session.commit()

    return count


def update_overdue_statuses(target_date=None):
    """Actualizar status de cuotas vencidas (sin penalizar, solo marcar).

    Cuotas pendientes pasadas de fecha → 'overdue' o 'grace'.
    """
    if target_date is None:
        target_date = date.today()

    installments = PaymentInstallment.query.join(
        PaymentPlan
    ).filter(
        PaymentInstallment.status == 'pending',
        PaymentInstallment.due_date < target_date,
        PaymentPlan.status == 'active',
    ).all()

    for inst in installments:
        grace_days = inst.plan.grace_days
        days_overdue = (target_date - inst.due_date).days

        if days_overdue <= grace_days:
            inst.status = 'grace'
        else:
            inst.status = 'overdue'

    if installments:
        db.session.commit()

    return len(installments)


# ──────────────────────────────────────────────
# Consultas de cobranza
# ──────────────────────────────────────────────

def get_collection_agenda(collector_id=None, target_date=None, view_all=False):
    """Obtener agenda de cobranza: cuotas que vencen hoy o están atrasadas.

    Returns:
        Lista de dicts con info de cada cuota a cobrar
    """
    if target_date is None:
        target_date = date.today()

    query = PaymentInstallment.query.join(
        PaymentPlan
    ).join(
        Sale, PaymentPlan.sale_id == Sale.id
    ).filter(
        PaymentInstallment.status.in_(['pending', 'partial', 'overdue', 'grace']),
        PaymentInstallment.due_date <= target_date,
        PaymentPlan.status == 'active',
        Sale.status == 'active',
    )

    if not view_all and collector_id:
        query = query.filter(Sale.agent_id == collector_id)

    installments = query.order_by(
        PaymentInstallment.due_date,
        PaymentInstallment.installment_num,
    ).all()

    agenda = []
    for inst in installments:
        plan = inst.plan
        sale = plan.sale
        customer = sale.customer
        owed = inst.expected_amount + inst.penalty_amount - inst.paid_amount
        days_overdue = (target_date - inst.due_date).days if target_date > inst.due_date else 0

        agenda.append({
            'installment': inst,
            'sale': sale,
            'customer': customer,
            'plan': plan,
            'owed': owed,
            'days_overdue': days_overdue,
        })

    return agenda


def get_upcoming_installments(collector_id=None, days_ahead=7, view_all=False):
    """Obtener cuotas próximas a vencer."""
    from datetime import timedelta
    today = date.today()
    future = today + timedelta(days=days_ahead)

    query = PaymentInstallment.query.join(
        PaymentPlan
    ).join(
        Sale, PaymentPlan.sale_id == Sale.id
    ).filter(
        PaymentInstallment.status == 'pending',
        PaymentInstallment.due_date > today,
        PaymentInstallment.due_date <= future,
        PaymentPlan.status == 'active',
        Sale.status == 'active',
    )

    if not view_all and collector_id:
        query = query.filter(Sale.agent_id == collector_id)

    return query.order_by(PaymentInstallment.due_date).all()


def get_collection_history(collector_id=None, sale_id=None, limit=50):
    """Historial de pagos registrados."""
    query = Payment.query

    if collector_id:
        query = query.filter_by(collected_by=collector_id)

    if sale_id:
        query = query.join(PaymentInstallment).join(PaymentPlan).filter(
            PaymentPlan.sale_id == sale_id,
        )

    return query.order_by(Payment.created_at.desc()).limit(limit).all()


def get_collection_stats(collector_id=None, view_all=False):
    """Estadísticas de cobranza."""
    from sqlalchemy import func
    today = date.today()

    # Base query para cuotas activas
    base = PaymentInstallment.query.join(PaymentPlan).join(
        Sale, PaymentPlan.sale_id == Sale.id
    ).filter(
        PaymentPlan.status == 'active',
        Sale.status == 'active',
    )

    if not view_all and collector_id:
        base = base.filter(Sale.agent_id == collector_id)

    # Total cobrado hoy
    collected_today = db.session.query(
        func.coalesce(func.sum(Payment.amount), 0)
    ).filter(
        func.date(Payment.payment_date) == today,
    )
    if not view_all and collector_id:
        collected_today = collected_today.filter(Payment.collected_by == collector_id)
    collected_today = collected_today.scalar()

    # Cuotas vencidas
    overdue_count = base.filter(
        PaymentInstallment.status == 'overdue',
    ).count()

    # Cuotas pendientes hoy
    due_today = base.filter(
        PaymentInstallment.due_date == today,
        PaymentInstallment.status.in_(['pending', 'partial']),
    ).count()

    # Total pendiente de cobrar
    pending_total = db.session.query(
        func.coalesce(
            func.sum(
                PaymentInstallment.expected_amount
                + PaymentInstallment.penalty_amount
                - PaymentInstallment.paid_amount
            ), 0
        )
    ).join(PaymentPlan).join(
        Sale, PaymentPlan.sale_id == Sale.id
    ).filter(
        PaymentInstallment.status.in_(['pending', 'partial', 'overdue', 'grace']),
        PaymentPlan.status == 'active',
        Sale.status == 'active',
    )
    if not view_all and collector_id:
        pending_total = pending_total.filter(Sale.agent_id == collector_id)
    pending_total = pending_total.scalar()

    return {
        'collected_today': collected_today,
        'overdue_count': overdue_count,
        'due_today': due_today,
        'pending_total': pending_total,
    }
