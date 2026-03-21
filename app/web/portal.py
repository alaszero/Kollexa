"""Vistas web del portal de clientes (sin login, acceso por token)."""
from flask import Blueprint, render_template, abort, request, url_for, flash, redirect
from flask_login import login_required, current_user
from app.services import portal_service as ps
from app.services import customer_service as cs
from app.utils.decorators import permission_required
from app.utils.helpers import whatsapp_url
from app.extensions import csrf

portal_bp = Blueprint('portal', __name__, url_prefix='/portal')


@portal_bp.route('/<token>')
def view(token):
    """Vista pública del portal — el cliente accede con su link."""
    data = ps.get_portal_by_token(token)
    if not data:
        return render_template('portal/invalid.html'), 404

    return render_template('portal/view.html', **data)


@portal_bp.route('/<token>/sale/<int:sale_id>')
def sale_detail(token, sale_id):
    """Detalle de una venta dentro del portal."""
    data = ps.get_portal_by_token(token)
    if not data:
        return render_template('portal/invalid.html'), 404

    # Buscar la venta en los datos del portal
    sale_data = None
    for sd in data['sales']:
        if sd['sale'].id == sale_id:
            sale_data = sd
            break

    if not sale_data:
        return render_template('portal/invalid.html'), 404

    return render_template(
        'portal/sale_detail.html',
        customer=data['customer'],
        token=token,
        **sale_data,
    )


# ── Generación de tokens (desde panel admin/agente) ──

@portal_bp.route('/generate/<int:customer_id>', methods=['POST'])
@login_required
@permission_required('customers.view')
def generate_token(customer_id):
    """Generar link de portal y redirigir a WhatsApp si hay teléfono."""
    sale_id = request.form.get('sale_id', type=int)
    token = ps.generate_portal_token(
        customer_id=customer_id,
        sale_id=sale_id,
        user_id=current_user.id,
    )
    portal_url = url_for('portal.view', token=token.token, _external=True)

    # Intentar redirigir a WhatsApp
    customer = cs.get_customer_by_id(customer_id)
    if customer and customer.phone:
        message = f'Hola {customer.full_name}, consulta tu estado de cuenta aqui: {portal_url}'
        wa_url = whatsapp_url(customer.phone, message)
        if wa_url:
            flash(f'Link generado. Envialo por WhatsApp.', 'success')
            return redirect(wa_url)

    # Si no tiene teléfono, mostrar el link
    flash(f'Link generado: {portal_url}', 'success')
    return redirect(request.referrer or url_for('customers.detail', customer_id=customer_id))
