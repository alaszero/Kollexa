"""API REST de cobranza."""
from flask import request, jsonify
from app.api import api_bp
from app.extensions import csrf
from app.services import collection_service as col
from app.utils.decorators import api_permission_required
from app.utils.validators import validate_required, validate_positive_decimal


@api_bp.route('/collections/agenda', methods=['GET'])
@api_permission_required('collections.view')
def api_collection_agenda(current_api_user):
    view_all = current_api_user.has_permission('collections.view_all') or current_api_user.has_role('superadmin')
    collector_id = None if view_all else current_api_user.id

    agenda = col.get_collection_agenda(collector_id=collector_id, view_all=view_all)
    data = [
        {
            'installment_id': item['installment'].id,
            'installment_num': item['installment'].installment_num,
            'due_date': item['installment'].due_date.isoformat(),
            'expected_amount': str(item['installment'].expected_amount),
            'paid_amount': str(item['installment'].paid_amount),
            'penalty_amount': str(item['installment'].penalty_amount),
            'owed': str(item['owed']),
            'status': item['installment'].status,
            'days_overdue': item['days_overdue'],
            'customer_id': item['customer'].id,
            'customer_name': item['customer'].full_name,
            'customer_phone': item['customer'].phone,
            'customer_address': item['customer'].address,
            'sale_id': item['sale'].id,
            'sale_total': str(item['sale'].total),
        }
        for item in agenda
    ]
    return jsonify({'data': data}), 200


@api_bp.route('/collections/upcoming', methods=['GET'])
@api_permission_required('collections.view')
def api_upcoming_installments(current_api_user):
    view_all = current_api_user.has_permission('collections.view_all') or current_api_user.has_role('superadmin')
    collector_id = None if view_all else current_api_user.id
    days = request.args.get('days', 7, type=int)

    installments = col.get_upcoming_installments(
        collector_id=collector_id, days_ahead=days, view_all=view_all,
    )
    data = [inst.to_dict() for inst in installments]
    return jsonify({'data': data}), 200


@api_bp.route('/collections/stats', methods=['GET'])
@api_permission_required('collections.view')
def api_collection_stats(current_api_user):
    view_all = current_api_user.has_permission('collections.view_all') or current_api_user.has_role('superadmin')
    collector_id = None if view_all else current_api_user.id

    stats = col.get_collection_stats(collector_id=collector_id, view_all=view_all)
    return jsonify({
        'data': {k: str(v) for k, v in stats.items()}
    }), 200


@api_bp.route('/collections/pay', methods=['POST'])
@csrf.exempt
@api_permission_required('collections.collect')
def api_collect_payment(current_api_user):
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Se requiere JSON'}), 400

    errors = validate_required(data, 'installment_id', 'amount')
    err = validate_positive_decimal(data.get('amount', 0), 'amount')
    if err:
        errors.append(err)
    if errors:
        return jsonify({'error': 'Validación fallida', 'details': errors}), 400

    try:
        payments = col.collect_payment(
            installment_id=int(data['installment_id']),
            amount=data['amount'],
            collected_by=current_api_user.id,
            payment_method=data.get('payment_method', 'cash'),
            notes=data.get('notes'),
            latitude=data.get('latitude'),
            longitude=data.get('longitude'),
        )
        return jsonify({
            'data': [p.to_dict() for p in payments],
            'message': f'Pago de ${data["amount"]} registrado ({len(payments)} cuota(s) afectada(s))',
        }), 201
    except col.CollectionError as e:
        return jsonify({'error': str(e)}), 400


@api_bp.route('/collections/history', methods=['GET'])
@api_permission_required('collections.view')
def api_collection_history(current_api_user):
    view_all = current_api_user.has_permission('collections.view_all') or current_api_user.has_role('superadmin')
    collector_id = request.args.get('collector_id', type=int)
    sale_id = request.args.get('sale_id', type=int)

    if not view_all:
        collector_id = current_api_user.id

    payments = col.get_collection_history(
        collector_id=collector_id, sale_id=sale_id,
    )
    data = [p.to_dict() for p in payments]
    return jsonify({'data': data}), 200


@api_bp.route('/collections/apply-penalties', methods=['POST'])
@csrf.exempt
@api_permission_required('config.edit')
def api_apply_penalties(current_api_user):
    """Ejecutar penalizaciones manualmente (normalmente se haría por cron)."""
    count = col.apply_penalties_for_date()
    updated = col.update_overdue_statuses()
    return jsonify({
        'data': {
            'penalties_applied': count,
            'statuses_updated': updated,
        },
        'message': f'{count} penalizaciones aplicadas, {updated} estados actualizados',
    }), 200
