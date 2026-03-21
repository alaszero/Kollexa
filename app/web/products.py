"""Vistas web de productos."""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.services import product_service as ps
from app.utils.decorators import permission_required

products_bp = Blueprint('products', __name__, url_prefix='/products')


@products_bp.route('/')
@login_required
@permission_required('products.view')
def index():
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()

    view = request.args.get('view', 'grid')

    query = ps.get_products_query(
        search=search or None,
        category=category or None,
        active_only=False,
    )
    products = query.all()
    categories = ps.get_categories()

    # Obtener unidades vendidas y stock para cada producto
    product_ids = [p.id for p in products]
    units_sold = ps.get_units_sold(product_ids) if product_ids else {}
    stock = ps.get_product_stock(product_ids) if product_ids else {}

    return render_template(
        'products/index.html',
        products=products,
        categories=categories,
        search=search,
        current_category=category,
        units_sold=units_sold,
        stock=stock,
        view=view,
    )


@products_bp.route('/new', methods=['GET', 'POST'])
@login_required
@permission_required('products.create')
def create():
    if request.method == 'POST':
        data = {
            'sku': request.form.get('sku', '').strip() or None,
            'name': request.form.get('name', '').strip(),
            'description': request.form.get('description', '').strip() or None,
            'base_price': request.form.get('base_price'),
            'sell_price': request.form.get('sell_price'),
            'category': request.form.get('category', '').strip() or None,
        }

        if not data['sku'] or not data['name'] or not data['base_price'] or not data['sell_price']:
            flash('SKU, nombre, precio base y precio venta son requeridos.', 'error')
            return render_template('products/form.html', product=None, data=data,
                                   categories=ps.get_categories())

        try:
            product = ps.create_product(data, user_id=current_user.id)
            flash(f'Producto "{product.name}" creado.', 'success')
            return redirect(url_for('products.index'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')

    categories = ps.get_categories()
    return render_template('products/form.html', product=None, data={}, categories=categories)


@products_bp.route('/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('products.edit')
def edit(product_id):
    product = ps.get_product_by_id(product_id)
    if not product:
        flash('Producto no encontrado.', 'error')
        return redirect(url_for('products.index'))

    if request.method == 'POST':
        data = {
            'sku': request.form.get('sku', '').strip() or None,
            'name': request.form.get('name', '').strip(),
            'description': request.form.get('description', '').strip() or None,
            'base_price': request.form.get('base_price'),
            'sell_price': request.form.get('sell_price'),
            'category': request.form.get('category', '').strip() or None,
        }

        if not data['sku'] or not data['name'] or not data['base_price'] or not data['sell_price']:
            flash('SKU, nombre, precio base y precio venta son requeridos.', 'error')
            return render_template('products/form.html', product=product, data=data,
                                   categories=ps.get_categories())

        try:
            ps.update_product(product, data, user_id=current_user.id)
            flash(f'Producto "{product.name}" actualizado.', 'success')
            return redirect(url_for('products.index'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')

    categories = ps.get_categories()
    return render_template('products/form.html', product=product, data={}, categories=categories)


@products_bp.route('/<int:product_id>/toggle', methods=['POST'])
@login_required
@permission_required('products.edit')
def toggle(product_id):
    product = ps.get_product_by_id(product_id)
    if product:
        ps.toggle_product(product, user_id=current_user.id)
        state = 'activado' if product.is_active else 'desactivado'
        flash(f'Producto "{product.name}" {state}.', 'info')
    return redirect(url_for('products.index'))
