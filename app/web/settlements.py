"""Vistas web de liquidaciones de cobradores."""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.services import settlement_service as ss
from app.utils.decorators import permission_required
from app.extensions import db

settlements_bp = Blueprint('settlements', __name__, url_prefix='/settlements')


@settlements_bp.route('/')
@login_required
@permission_required('collections.view_all')
def index():
    """Vista principal: resumen de dinero en transito por agente."""
    summary = ss.get_agents_settlement_summary()

    # Liquidaciones recientes
    recent = ss.get_settlements_query().limit(20).all()

    # Total en transito
    total_in_transit = sum(s['unsettled_amount'] for s in summary)

    return render_template(
        'settlements/index.html',
        summary=summary,
        recent=recent,
        total_in_transit=total_in_transit,
    )


@settlements_bp.route('/create/<int:agent_id>', methods=['POST'])
@login_required
@permission_required('collections.view_all')
def create(agent_id):
    """Crear liquidacion para un agente."""
    settlement = ss.create_settlement(
        agent_id=agent_id,
        created_by=current_user.id,
    )
    if settlement:
        flash(f'Liquidacion #{settlement.id} creada por ${settlement.total_amount} ({settlement.payment_count} pagos).', 'success')
    else:
        flash('No hay pagos pendientes de liquidar para este agente.', 'info')

    return redirect(url_for('settlements.index'))


@settlements_bp.route('/<int:settlement_id>')
@login_required
@permission_required('collections.view_all')
def detail(settlement_id):
    """Detalle de una liquidacion."""
    settlement = ss.get_settlement_by_id(settlement_id)
    if not settlement:
        flash('Liquidacion no encontrada.', 'error')
        return redirect(url_for('settlements.index'))

    details = settlement.details.all()
    return render_template(
        'settlements/detail.html',
        settlement=settlement,
        details=details,
    )


@settlements_bp.route('/<int:settlement_id>/confirm', methods=['POST'])
@login_required
@permission_required('collections.view_all')
def confirm(settlement_id):
    """Confirmar recepcion del dinero."""
    try:
        settlement = ss.confirm_settlement(settlement_id, current_user.id)
        flash(f'Liquidacion #{settlement.id} confirmada. Dinero recibido.', 'success')
    except ss.SettlementError as e:
        flash(str(e), 'error')
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')

    return redirect(url_for('settlements.detail', settlement_id=settlement_id))
