"""Vistas web de ventas."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.services import sale_service as ss
from app.services import customer_service as cs
from app.services import product_service as ps
from app.services import inventory_service as inv
from app.models.user import User
from app.utils.decorators import permission_required

sales_bp = Blueprint('sales', __name__, url_prefix='/sales')


@sales_bp.route('/')
@login_required
@permission_required('sales.view')
def index():
    status = request.args.get('status', '').strip()
    customer_id = request.args.get('customer_id', type=int)

    # Si no tiene permiso view_all, solo ve sus propias ventas
    agent_id = None
    if not current_user.has_permission('sales.view_all') and not current_user.has_role('superadmin'):
        agent_id = current_user.id

    query = ss.get_sales_query(
        customer_id=customer_id,
        agent_id=agent_id,
        status=status or None,
    )
    sales = query.all()

    sales_data = []
    for sale in sales:
        summary = ss.get_sale_summary(sale)
        sales_data.append({'sale': sale, 'summary': summary})

    return render_template('sales/index.html', sales_data=sales_data, current_status=status)


@sales_bp.route('/new', methods=['GET', 'POST'])
@login_required
@permission_required('sales.create')
def create():
    if request.method == 'POST':
        customer_id = request.form.get('customer_id', type=int)
        num_installments = request.form.get('num_installments', 10, type=int)
        notes = request.form.get('notes', '').strip()

        # Recoger items del formulario dinámico
        items = []
        product_ids = request.form.getlist('product_id[]')
        quantities = request.form.getlist('quantity[]')
        unit_prices = request.form.getlist('unit_price[]')

        for i, pid in enumerate(product_ids):
            if pid and quantities[i]:
                item = {'product_id': int(pid), 'quantity': int(quantities[i])}
                if i < len(unit_prices) and unit_prices[i]:
                    item['unit_price'] = unit_prices[i]
                items.append(item)

        if not customer_id:
            flash('Selecciona un cliente.', 'error')
        elif not items:
            flash('Agrega al menos un producto.', 'error')
        else:
            try:
                sale = ss.create_sale(
                    data={
                        'customer_id': customer_id,
                        'items': items,
                        'num_installments': num_installments,
                        'notes': notes or None,
                    },
                    agent_id=current_user.id,
                )
                flash(f'Venta #{sale.id} registrada por ${sale.total:.2f}', 'success')
                return redirect(url_for('sales.detail', sale_id=sale.id))
            except ss.SaleValidationError as e:
                flash(str(e), 'error')
            except inv.InsufficientStockError as e:
                flash(str(e), 'error')
            except Exception as e:
                flash(f'Error: {str(e)}', 'error')

    # Datos para el formulario
    customers = cs.get_customers_query().all()

    # Productos disponibles con stock del agente
    agent_location = inv.get_agent_location(current_user.id)
    agent_stock = {}
    if agent_location:
        for item, product in inv.get_stock_by_location(agent_location.id):
            agent_stock[product.id] = {
                'product': product,
                'quantity': item.quantity,
            }

    products = ps.get_products_query().all()

    return render_template(
        'sales/form.html',
        customers=customers,
        products=products,
        agent_stock=agent_stock,
    )


@sales_bp.route('/<int:sale_id>')
@login_required
@permission_required('sales.view')
def detail(sale_id):
    sale = ss.get_sale_full(sale_id)
    if not sale:
        flash('Venta no encontrada.', 'error')
        return redirect(url_for('sales.index'))

    # Verificar acceso
    if not current_user.has_permission('sales.view_all') and not current_user.has_role('superadmin'):
        if sale.agent_id != current_user.id:
            flash('No tienes acceso a esta venta.', 'error')
            return redirect(url_for('sales.index'))

    summary = ss.get_sale_summary(sale)

    return render_template('sales/detail.html', sale=sale, summary=summary)


@sales_bp.route('/<int:sale_id>/cancel', methods=['POST'])
@login_required
@permission_required('sales.cancel')
def cancel(sale_id):
    sale = ss.get_sale_by_id(sale_id)
    if not sale:
        flash('Venta no encontrada.', 'error')
        return redirect(url_for('sales.index'))

    try:
        ss.cancel_sale(sale, user_id=current_user.id)
        flash(f'Venta #{sale.id} cancelada.', 'info')
    except ss.SaleValidationError as e:
        flash(str(e), 'error')

    return redirect(url_for('sales.detail', sale_id=sale.id))
