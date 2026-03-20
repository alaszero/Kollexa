"""API REST de inventario."""
from flask import request, jsonify
from app.api import api_bp
from app.extensions import csrf
from app.services import inventory_service as inv
from app.utils.decorators import api_auth_required, api_permission_required
from app.utils.helpers import get_pagination_params, paginated_response
from app.utils.validators import validate_required, validate_positive_integer


@api_bp.route('/inventory/stock', methods=['GET'])
@api_permission_required('inventory.view')
def api_global_stock(current_api_user):
    rows = inv.get_global_stock()
    data = [
        {
            'product_id': r.id,
            'product_name': r.name,
            'sku': r.sku,
            'location_type': r.type,
            'location_name': r.location_name,
            'quantity': r.quantity,
        }
        for r in rows
    ]
    return jsonify({'data': data}), 200


@api_bp.route('/inventory/stock/warehouse', methods=['GET'])
@api_permission_required('inventory.view')
def api_warehouse_stock(current_api_user):
    warehouse = inv.get_warehouse()
    if not warehouse:
        return jsonify({'error': 'Almacén no encontrado'}), 404

    items = inv.get_stock_by_location(warehouse.id)
    data = [
        {
            'product_id': product.id,
            'product_name': product.name,
            'sku': product.sku,
            'quantity': item.quantity,
        }
        for item, product in items
    ]
    return jsonify({'data': data, 'location': warehouse.to_dict()}), 200


@api_bp.route('/inventory/stock/agent/<int:user_id>', methods=['GET'])
@api_permission_required('inventory.view_agent_stock')
def api_agent_stock(user_id, current_api_user):
    location = inv.get_agent_location(user_id)
    if not location:
        return jsonify({'error': 'Ubicación de agente no encontrada'}), 404

    items = inv.get_stock_by_location(location.id)
    data = [
        {
            'product_id': product.id,
            'product_name': product.name,
            'sku': product.sku,
            'quantity': item.quantity,
        }
        for item, product in items
    ]
    return jsonify({'data': data, 'location': location.to_dict()}), 200


@api_bp.route('/inventory/stock/agents', methods=['GET'])
@api_permission_required('inventory.view_agent_stock')
def api_agents_stock_summary(current_api_user):
    rows = inv.get_agents_stock_summary()
    data = [
        {
            'user_id': r.id,
            'agent_name': r.full_name,
            'location_id': r.location_id,
            'total_items': int(r.total_items),
            'product_count': int(r.product_count),
        }
        for r in rows
    ]
    return jsonify({'data': data}), 200


@api_bp.route('/inventory/purchase', methods=['POST'])
@csrf.exempt
@api_permission_required('inventory.purchase')
def api_purchase_stock(current_api_user):
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Se requiere JSON'}), 400

    errors = validate_required(data, 'product_id', 'quantity')
    err = validate_positive_integer(data.get('quantity', 0), 'quantity')
    if err:
        errors.append(err)

    if errors:
        return jsonify({'error': 'Validación fallida', 'details': errors}), 400

    warehouse = inv.get_warehouse()
    if not warehouse:
        return jsonify({'error': 'Almacén no configurado'}), 500

    try:
        item = inv.purchase_stock(
            product_id=int(data['product_id']),
            quantity=int(data['quantity']),
            warehouse_id=warehouse.id,
            performed_by=current_api_user.id,
            notes=data.get('notes'),
        )
        return jsonify({'data': item.to_dict(), 'message': 'Compra registrada'}), 201
    except inv.InvalidMovementError as e:
        return jsonify({'error': str(e)}), 400


@api_bp.route('/inventory/dispatch', methods=['POST'])
@csrf.exempt
@api_permission_required('inventory.dispatch')
def api_dispatch_stock(current_api_user):
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Se requiere JSON'}), 400

    errors = validate_required(data, 'product_id', 'quantity', 'agent_user_id')
    err = validate_positive_integer(data.get('quantity', 0), 'quantity')
    if err:
        errors.append(err)

    if errors:
        return jsonify({'error': 'Validación fallida', 'details': errors}), 400

    warehouse = inv.get_warehouse()
    if not warehouse:
        return jsonify({'error': 'Almacén no configurado'}), 500

    agent_location = inv.get_agent_location(int(data['agent_user_id']))
    if not agent_location:
        return jsonify({'error': 'Ubicación de agente no encontrada'}), 404

    try:
        item = inv.dispatch_to_agent(
            product_id=int(data['product_id']),
            quantity=int(data['quantity']),
            warehouse_id=warehouse.id,
            agent_location_id=agent_location.id,
            performed_by=current_api_user.id,
            notes=data.get('notes'),
        )
        return jsonify({'data': item.to_dict(), 'message': 'Surtido registrado'}), 201
    except inv.InsufficientStockError as e:
        return jsonify({'error': str(e)}), 409
    except inv.InvalidMovementError as e:
        return jsonify({'error': str(e)}), 400


@api_bp.route('/inventory/return', methods=['POST'])
@csrf.exempt
@api_permission_required('inventory.return')
def api_return_stock(current_api_user):
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Se requiere JSON'}), 400

    errors = validate_required(data, 'product_id', 'quantity', 'agent_user_id')
    err = validate_positive_integer(data.get('quantity', 0), 'quantity')
    if err:
        errors.append(err)

    if errors:
        return jsonify({'error': 'Validación fallida', 'details': errors}), 400

    warehouse = inv.get_warehouse()
    if not warehouse:
        return jsonify({'error': 'Almacén no configurado'}), 500

    agent_location = inv.get_agent_location(int(data['agent_user_id']))
    if not agent_location:
        return jsonify({'error': 'Ubicación de agente no encontrada'}), 404

    try:
        item = inv.return_to_warehouse(
            product_id=int(data['product_id']),
            quantity=int(data['quantity']),
            agent_location_id=agent_location.id,
            warehouse_id=warehouse.id,
            performed_by=current_api_user.id,
            notes=data.get('notes'),
        )
        return jsonify({'data': item.to_dict(), 'message': 'Devolución registrada'}), 201
    except inv.InsufficientStockError as e:
        return jsonify({'error': str(e)}), 409
    except inv.InvalidMovementError as e:
        return jsonify({'error': str(e)}), 400


@api_bp.route('/inventory/movements', methods=['GET'])
@api_permission_required('inventory.view')
def api_movements(current_api_user):
    product_id = request.args.get('product_id', type=int)
    location_id = request.args.get('location_id', type=int)
    movement_type = request.args.get('type')

    query = inv.get_movements_query(
        product_id=product_id,
        location_id=location_id,
        movement_type=movement_type,
    )
    page, per_page = get_pagination_params()
    return jsonify(paginated_response(query, page, per_page)), 200


@api_bp.route('/inventory/reconciliation', methods=['GET'])
@api_permission_required('inventory.reconcile')
def api_reconciliation(current_api_user):
    data = inv.get_reconciliation()
    return jsonify({'data': data}), 200
