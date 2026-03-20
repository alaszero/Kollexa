"""API del portal de clientes."""
from flask import request, jsonify
from app.api import api_bp
from app.extensions import csrf
from app.services import portal_service as ps
from app.utils.decorators import api_permission_required


@api_bp.route('/portal/generate', methods=['POST'])
@csrf.exempt
@api_permission_required('customers.view')
def api_generate_portal_token(current_api_user):
    data = request.get_json()
    if not data or 'customer_id' not in data:
        return jsonify({'error': 'customer_id es requerido'}), 400

    token = ps.generate_portal_token(
        customer_id=int(data['customer_id']),
        sale_id=data.get('sale_id'),
        expires_days=data.get('expires_days', 90),
        user_id=current_api_user.id,
    )

    return jsonify({
        'data': {
            'token': token.token,
            'portal_url': f'/portal/{token.token}',
            'expires_at': token.expires_at.isoformat() if token.expires_at else None,
        }
    }), 201


@api_bp.route('/portal/<token_str>', methods=['GET'])
@csrf.exempt
def api_portal_view(token_str):
    """Endpoint público: ver datos del portal por token."""
    data = ps.get_portal_by_token(token_str)
    if not data:
        return jsonify({'error': 'Token inválido o expirado'}), 404

    customer = data['customer']
    sales = []
    for sd in data['sales']:
        sale = sd['sale']
        sales.append({
            'sale_id': sale.id,
            'sale_date': sale.sale_date.isoformat() if sale.sale_date else None,
            'total': str(sale.total),
            'status': sale.status,
            'paid': str(sd['paid']),
            'remaining': str(sd['remaining']),
            'progress': sd['progress'],
            'installments_paid': sd['installments_paid'],
            'total_installments': sd['total_installments'],
            'next_due_date': sd['next_installment'].due_date.isoformat() if sd['next_installment'] else None,
            'next_amount': str(sd['next_installment'].expected_amount + sd['next_installment'].penalty_amount - sd['next_installment'].paid_amount) if sd['next_installment'] else None,
        })

    return jsonify({
        'data': {
            'customer_name': customer.full_name,
            'total_debt': str(data['total_debt']),
            'total_paid': str(data['total_paid']),
            'sales': sales,
        }
    }), 200
