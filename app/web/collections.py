"""Vistas web de cobranza."""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.services import collection_service as col
from app.services import sale_service as ss
from app.models.payment import PaymentInstallment, PaymentPlan
from app.models.sale import Sale
from app.utils.decorators import permission_required

collections_bp = Blueprint('collections', __name__, url_prefix='/collections')


@collections_bp.route('/')
@login_required
@permission_required('collections.view')
def index():
    """Agenda de cobranza: qué se cobra hoy."""
    view_all = current_user.has_permission('collections.view_all') or current_user.has_role('superadmin')
    collector_id = None if view_all else current_user.id

    # Actualizar estados de cuotas vencidas
    col.update_overdue_statuses()

    agenda = col.get_collection_agenda(collector_id=collector_id, view_all=view_all)
    stats = col.get_collection_stats(collector_id=collector_id, view_all=view_all)
    upcoming = col.get_upcoming_installments(collector_id=collector_id, view_all=view_all)

    return render_template(
        'collections/index.html',
        agenda=agenda,
        stats=stats,
        upcoming=upcoming,
        view_all=view_all,
    )


@collections_bp.route('/pay/<int:installment_id>', methods=['GET', 'POST'])
@login_required
@permission_required('collections.collect')
def pay(installment_id):
    """Registrar pago de una cuota."""
    installment = db.session.get(PaymentInstallment, installment_id)
    if not installment:
        flash('Cuota no encontrada.', 'error')
        return redirect(url_for('collections.index'))

    plan = installment.plan
    sale = plan.sale
    customer = sale.customer
    owed = installment.expected_amount + installment.penalty_amount - installment.paid_amount

    if request.method == 'POST':
        amount = request.form.get('amount', type=float)
        payment_method = request.form.get('payment_method', 'cash')
        notes = request.form.get('notes', '').strip()

        if not amount or amount <= 0:
            flash('El monto debe ser mayor a cero.', 'error')
        else:
            try:
                payments = col.collect_payment(
                    installment_id=installment_id,
                    amount=amount,
                    collected_by=current_user.id,
                    payment_method=payment_method,
                    notes=notes or None,
                )
                affected = len(payments)
                flash(f'Pago de ${amount:.2f} registrado ({affected} cuota{"s" if affected > 1 else ""}).', 'success')
                return redirect(url_for('collections.index'))
            except col.CollectionError as e:
                flash(str(e), 'error')

    return render_template(
        'collections/pay.html',
        installment=installment,
        plan=plan,
        sale=sale,
        customer=customer,
        owed=owed,
    )


@collections_bp.route('/sale/<int:sale_id>')
@login_required
@permission_required('collections.view')
def sale_payments(sale_id):
    """Ver historial de pagos de una venta."""
    sale = ss.get_sale_full(sale_id)
    if not sale:
        flash('Venta no encontrada.', 'error')
        return redirect(url_for('collections.index'))

    payments = col.get_collection_history(sale_id=sale_id, limit=100)
    summary = ss.get_sale_summary(sale)

    return render_template(
        'collections/sale_payments.html',
        sale=sale,
        payments=payments,
        summary=summary,
    )


@collections_bp.route('/history')
@login_required
@permission_required('collections.view')
def history():
    """Historial general de pagos."""
    view_all = current_user.has_permission('collections.view_all') or current_user.has_role('superadmin')
    collector_id = None if view_all else current_user.id

    payments = col.get_collection_history(collector_id=collector_id, limit=100)

    return render_template('collections/history.html', payments=payments, view_all=view_all)
