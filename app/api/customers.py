"""API REST de clientes."""
from flask import request, jsonify
from app.api import api_bp
from app.extensions import csrf
from app.services import customer_service as cs
from app.utils.decorators import api_auth_required, api_permission_required
from app.utils.helpers import get_pagination_params, paginated_response
from app.utils.validators import validate_required


@api_bp.route('/customers', methods=['GET'])
@api_permission_required('customers.view')
def api_list_customers(current_api_user):
    search = request.args.get('search')
    neighborhood = request.args.get('neighborhood')
    active_only = request.args.get('active_only', 'true').lower() == 'true'

    query = cs.get_customers_query(search=search, neighborhood=neighborhood, active_only=active_only)
    page, per_page = get_pagination_params()
    return jsonify(paginated_response(query, page, per_page)), 200


@api_bp.route('/customers/<int:customer_id>', methods=['GET'])
@api_permission_required('customers.view')
def api_get_customer(customer_id, current_api_user):
    customer = cs.get_customer_by_id(customer_id)
    if not customer:
        return jsonify({'error': 'Cliente no encontrado'}), 404
    return jsonify({'data': customer.to_dict()}), 200


@api_bp.route('/customers', methods=['POST'])
@csrf.exempt
@api_permission_required('customers.create')
def api_create_customer(current_api_user):
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Se requiere JSON'}), 400

    errors = validate_required(data, 'full_name')
    if errors:
        return jsonify({'error': 'Validación fallida', 'details': errors}), 400

    customer = cs.create_customer(data, user_id=current_api_user.id)
    return jsonify({'data': customer.to_dict()}), 201


@api_bp.route('/customers/<int:customer_id>', methods=['PUT'])
@csrf.exempt
@api_permission_required('customers.edit')
def api_update_customer(customer_id, current_api_user):
    customer = cs.get_customer_by_id(customer_id)
    if not customer:
        return jsonify({'error': 'Cliente no encontrado'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Se requiere JSON'}), 400

    customer = cs.update_customer(customer, data, user_id=current_api_user.id)
    return jsonify({'data': customer.to_dict()}), 200


@api_bp.route('/customers/<int:customer_id>/toggle', methods=['POST'])
@csrf.exempt
@api_permission_required('customers.edit')
def api_toggle_customer(customer_id, current_api_user):
    customer = cs.get_customer_by_id(customer_id)
    if not customer:
        return jsonify({'error': 'Cliente no encontrado'}), 404

    customer = cs.toggle_customer(customer, user_id=current_api_user.id)
    return jsonify({'data': customer.to_dict()}), 200


@api_bp.route('/customers/neighborhoods', methods=['GET'])
@api_auth_required
def api_list_neighborhoods(current_api_user):
    return jsonify({'data': cs.get_neighborhoods()}), 200
