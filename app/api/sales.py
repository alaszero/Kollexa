"""API REST de ventas."""
from flask import request, jsonify
from app.api import api_bp
from app.extensions import csrf
from app.services import sale_service as ss
from app.utils.decorators import api_auth_required, api_permission_required
from app.utils.helpers import get_pagination_params, paginated_response
from app.utils.validators import validate_required


@api_bp.route('/sales', methods=['GET'])
@api_permission_required('sales.view')
def api_list_sales(current_api_user):
    customer_id = request.args.get('customer_id', type=int)
    agent_id = request.args.get('agent_id', type=int)
    status = request.args.get('status')

    # Si no tiene permiso sales.view_all, solo ve sus propias ventas
    if not current_api_user.has_permission('sales.view_all') and not current_api_user.has_role('superadmin'):
        agent_id = current_api_user.id

    query = ss.get_sales_query(customer_id=customer_id, agent_id=agent_id, status=status)
    page, per_page = get_pagination_params()
    return jsonify(paginated_response(query, page, per_page)), 200


@api_bp.route('/sales/<int:sale_id>', methods=['GET'])
@api_permission_required('sales.view')
def api_get_sale(sale_id, current_api_user):
    sale = ss.get_sale_full(sale_id)
    if not sale:
        return jsonify({'error': 'Venta no encontrada'}), 404

    # Verificar acceso
    if not current_api_user.has_permission('sales.view_all') and not current_api_user.has_role('superadmin'):
        if sale.agent_id != current_api_user.id:
            return jsonify({'error': 'Sin acceso a esta venta'}), 403

    data = sale.to_dict()
    data['details'] = [d.to_dict() for d in sale.details]
    data['summary'] = ss.get_sale_summary(sale)

    if sale.payment_plan:
        data['payment_plan'] = sale.payment_plan.to_dict()
        data['installments'] = [i.to_dict() for i in sale.payment_plan.installments]

    return jsonify({'data': data}), 200


@api_bp.route('/sales', methods=['POST'])
@csrf.exempt
@api_permission_required('sales.create')
def api_create_sale(current_api_user):
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Se requiere JSON'}), 400

    errors = validate_required(data, 'customer_id', 'items')
    if errors:
        return jsonify({'error': 'Validación fallida', 'details': errors}), 400

    if not isinstance(data.get('items'), list) or len(data['items']) == 0:
        return jsonify({'error': 'Se requiere al menos un producto'}), 400

    try:
        sale = ss.create_sale(data, agent_id=current_api_user.id)
        result = sale.to_dict()
        result['summary'] = ss.get_sale_summary(sale)
        return jsonify({'data': result, 'message': 'Venta registrada'}), 201
    except ss.SaleValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Error al crear venta: {str(e)}'}), 500


@api_bp.route('/sales/<int:sale_id>/cancel', methods=['POST'])
@csrf.exempt
@api_permission_required('sales.cancel')
def api_cancel_sale(sale_id, current_api_user):
    sale = ss.get_sale_by_id(sale_id)
    if not sale:
        return jsonify({'error': 'Venta no encontrada'}), 404

    try:
        sale = ss.cancel_sale(sale, user_id=current_api_user.id)
        return jsonify({'data': sale.to_dict(), 'message': 'Venta cancelada'}), 200
    except ss.SaleValidationError as e:
        return jsonify({'error': str(e)}), 400
