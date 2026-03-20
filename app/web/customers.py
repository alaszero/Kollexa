"""Vistas web de clientes."""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.services import customer_service as cs
from app.utils.decorators import permission_required

customers_bp = Blueprint('customers', __name__, url_prefix='/customers')


@customers_bp.route('/')
@login_required
@permission_required('customers.view')
def index():
    search = request.args.get('search', '').strip()
    neighborhood = request.args.get('neighborhood', '').strip()

    query = cs.get_customers_query(
        search=search or None,
        neighborhood=neighborhood or None,
        active_only=False,
    )
    customers = query.all()
    neighborhoods = cs.get_neighborhoods()

    return render_template(
        'customers/index.html',
        customers=customers,
        neighborhoods=neighborhoods,
        search=search,
        current_neighborhood=neighborhood,
    )


@customers_bp.route('/new', methods=['GET', 'POST'])
@login_required
@permission_required('customers.create')
def create():
    if request.method == 'POST':
        data = {
            'full_name': request.form.get('full_name', '').strip(),
            'phone': request.form.get('phone', '').strip() or None,
            'address': request.form.get('address', '').strip() or None,
            'neighborhood': request.form.get('neighborhood', '').strip() or None,
            'city': request.form.get('city', '').strip() or None,
            'reference': request.form.get('reference', '').strip() or None,
            'notes': request.form.get('notes', '').strip() or None,
        }

        if not data['full_name']:
            flash('El nombre es requerido.', 'error')
            return render_template('customers/form.html', customer=None, data=data,
                                   neighborhoods=cs.get_neighborhoods())

        try:
            customer = cs.create_customer(data, user_id=current_user.id)
            flash(f'Cliente "{customer.full_name}" registrado.', 'success')
            return redirect(url_for('customers.index'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')

    neighborhoods = cs.get_neighborhoods()
    return render_template('customers/form.html', customer=None, data={}, neighborhoods=neighborhoods)


@customers_bp.route('/<int:customer_id>')
@login_required
@permission_required('customers.view')
def detail(customer_id):
    customer = cs.get_customer_by_id(customer_id)
    if not customer:
        flash('Cliente no encontrado.', 'error')
        return redirect(url_for('customers.index'))

    # Obtener ventas del cliente
    from app.services import sale_service as ss
    sales = ss.get_sales_query(customer_id=customer_id).all()
    sales_data = []
    for sale in sales:
        summary = ss.get_sale_summary(sale)
        sales_data.append({'sale': sale, 'summary': summary})

    return render_template('customers/detail.html', customer=customer, sales_data=sales_data)


@customers_bp.route('/<int:customer_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('customers.edit')
def edit(customer_id):
    customer = cs.get_customer_by_id(customer_id)
    if not customer:
        flash('Cliente no encontrado.', 'error')
        return redirect(url_for('customers.index'))

    if request.method == 'POST':
        data = {
            'full_name': request.form.get('full_name', '').strip(),
            'phone': request.form.get('phone', '').strip() or None,
            'address': request.form.get('address', '').strip() or None,
            'neighborhood': request.form.get('neighborhood', '').strip() or None,
            'city': request.form.get('city', '').strip() or None,
            'reference': request.form.get('reference', '').strip() or None,
            'notes': request.form.get('notes', '').strip() or None,
        }

        if not data['full_name']:
            flash('El nombre es requerido.', 'error')
            return render_template('customers/form.html', customer=customer, data=data,
                                   neighborhoods=cs.get_neighborhoods())

        try:
            cs.update_customer(customer, data, user_id=current_user.id)
            flash(f'Cliente "{customer.full_name}" actualizado.', 'success')
            return redirect(url_for('customers.detail', customer_id=customer.id))
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')

    neighborhoods = cs.get_neighborhoods()
    return render_template('customers/form.html', customer=customer, data={}, neighborhoods=neighborhoods)


@customers_bp.route('/<int:customer_id>/toggle', methods=['POST'])
@login_required
@permission_required('customers.edit')
def toggle(customer_id):
    customer = cs.get_customer_by_id(customer_id)
    if customer:
        cs.toggle_customer(customer, user_id=current_user.id)
        state = 'activado' if customer.is_active else 'desactivado'
        flash(f'Cliente "{customer.full_name}" {state}.', 'info')
    return redirect(url_for('customers.index'))
