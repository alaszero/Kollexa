"""API REST de productos."""
from flask import request, jsonify
from app.api import api_bp
from app.extensions import csrf
from app.services import product_service as ps
from app.utils.decorators import api_auth_required, api_permission_required
from app.utils.helpers import get_pagination_params, paginated_response
from app.utils.validators import validate_required, validate_positive_decimal


@api_bp.route('/products', methods=['GET'])
@api_auth_required
def api_list_products(current_api_user):
    search = request.args.get('search')
    category = request.args.get('category')
    active_only = request.args.get('active_only', 'true').lower() == 'true'

    query = ps.get_products_query(search=search, category=category, active_only=active_only)
    page, per_page = get_pagination_params()

    return jsonify(paginated_response(query, page, per_page)), 200


@api_bp.route('/products/<int:product_id>', methods=['GET'])
@api_auth_required
def api_get_product(product_id, current_api_user):
    product = ps.get_product_by_id(product_id)
    if not product:
        return jsonify({'error': 'Producto no encontrado'}), 404
    return jsonify({'data': product.to_dict()}), 200


@api_bp.route('/products', methods=['POST'])
@csrf.exempt
@api_permission_required('products.create')
def api_create_product(current_api_user):
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Se requiere JSON'}), 400

    errors = validate_required(data, 'name', 'base_price', 'sell_price')
    for field in ('base_price', 'sell_price'):
        if field in data:
            err = validate_positive_decimal(data[field], field)
            if err:
                errors.append(err)

    if errors:
        return jsonify({'error': 'Validación fallida', 'details': errors}), 400

    product = ps.create_product(data, user_id=current_api_user.id)
    return jsonify({'data': product.to_dict()}), 201


@api_bp.route('/products/<int:product_id>', methods=['PUT'])
@csrf.exempt
@api_permission_required('products.edit')
def api_update_product(product_id, current_api_user):
    product = ps.get_product_by_id(product_id)
    if not product:
        return jsonify({'error': 'Producto no encontrado'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Se requiere JSON'}), 400

    errors = []
    for field in ('base_price', 'sell_price'):
        if field in data:
            err = validate_positive_decimal(data[field], field)
            if err:
                errors.append(err)

    if errors:
        return jsonify({'error': 'Validación fallida', 'details': errors}), 400

    product = ps.update_product(product, data, user_id=current_api_user.id)
    return jsonify({'data': product.to_dict()}), 200


@api_bp.route('/products/<int:product_id>/toggle', methods=['POST'])
@csrf.exempt
@api_permission_required('products.edit')
def api_toggle_product(product_id, current_api_user):
    product = ps.get_product_by_id(product_id)
    if not product:
        return jsonify({'error': 'Producto no encontrado'}), 404

    product = ps.toggle_product(product, user_id=current_api_user.id)
    return jsonify({'data': product.to_dict()}), 200


@api_bp.route('/products/categories', methods=['GET'])
@api_auth_required
def api_list_categories(current_api_user):
    categories = ps.get_categories()
    return jsonify({'data': categories}), 200
