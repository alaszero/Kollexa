"""Vistas web de inventario."""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.services import inventory_service as inv
from app.services import product_service as ps
from app.models.user import User, Role
from app.utils.decorators import permission_required
from app.extensions import db

inventory_bp = Blueprint('inventory', __name__, url_prefix='/inventory')


@inventory_bp.route('/')
@login_required
@permission_required('inventory.view')
def index():
    """Vista principal: stock del almacén."""
    warehouse = inv.get_warehouse()
    if not warehouse:
        flash('Almacén no configurado.', 'error')
        return redirect(url_for('web.dashboard'))

    items = inv.get_stock_by_location(warehouse.id)
    return render_template('inventory/index.html', items=items, warehouse=warehouse)


@inventory_bp.route('/agents')
@login_required
@permission_required('inventory.view_agent_stock')
def agents_stock():
    """Stock por agente."""
    summary = inv.get_agents_stock_summary()
    return render_template('inventory/agents.html', agents=summary)


@inventory_bp.route('/agent/<int:user_id>')
@login_required
@permission_required('inventory.view_agent_stock')
def agent_detail(user_id):
    """Detalle de stock de un agente."""
    agent = db.session.get(User, user_id)
    if not agent:
        flash('Agente no encontrado.', 'error')
        return redirect(url_for('inventory.agents_stock'))

    location = inv.get_agent_location(user_id)
    if not location:
        flash('Este usuario no tiene ubicación de inventario.', 'error')
        return redirect(url_for('inventory.agents_stock'))

    items = inv.get_stock_by_location(location.id)
    return render_template('inventory/agent_detail.html', agent=agent, items=items, location=location)


@inventory_bp.route('/purchase', methods=['GET', 'POST'])
@login_required
@permission_required('inventory.purchase')
def purchase():
    """Registrar compra/entrada de mercancía."""
    if request.method == 'POST':
        product_id = request.form.get('product_id', type=int)
        quantity = request.form.get('quantity', type=int)
        notes = request.form.get('notes', '').strip()

        if not product_id or not quantity or quantity <= 0:
            flash('Producto y cantidad (> 0) son requeridos.', 'error')
        else:
            warehouse = inv.get_warehouse()
            try:
                inv.purchase_stock(
                    product_id=product_id,
                    quantity=quantity,
                    warehouse_id=warehouse.id,
                    performed_by=current_user.id,
                    notes=notes or None,
                )
                product = ps.get_product_by_id(product_id)
                flash(f'{quantity}x "{product.name}" ingresados al almacén.', 'success')
                return redirect(url_for('inventory.index'))
            except Exception as e:
                flash(f'Error: {str(e)}', 'error')

    products = ps.get_products_query().all()
    return render_template('inventory/purchase.html', products=products)


@inventory_bp.route('/dispatch', methods=['GET', 'POST'])
@login_required
@permission_required('inventory.dispatch')
def dispatch():
    """Surtir agente desde almacén."""
    if request.method == 'POST':
        agent_user_id = request.form.get('agent_user_id', type=int)
        product_id = request.form.get('product_id', type=int)
        quantity = request.form.get('quantity', type=int)
        notes = request.form.get('notes', '').strip()

        if not agent_user_id or not product_id or not quantity or quantity <= 0:
            flash('Agente, producto y cantidad son requeridos.', 'error')
        else:
            warehouse = inv.get_warehouse()
            agent_location = inv.get_agent_location(agent_user_id)

            if not agent_location:
                flash('El agente seleccionado no tiene ubicación de inventario.', 'error')
            else:
                try:
                    inv.dispatch_to_agent(
                        product_id=product_id,
                        quantity=quantity,
                        warehouse_id=warehouse.id,
                        agent_location_id=agent_location.id,
                        performed_by=current_user.id,
                        notes=notes or None,
                    )
                    product = ps.get_product_by_id(product_id)
                    agent = db.session.get(User, agent_user_id)
                    flash(f'{quantity}x "{product.name}" surtidos a {agent.full_name}.', 'success')
                    return redirect(url_for('inventory.index'))
                except inv.InsufficientStockError as e:
                    flash(str(e), 'error')
                except Exception as e:
                    flash(f'Error: {str(e)}', 'error')

    products = ps.get_products_query().all()
    # Obtener agentes (usuarios con rol agent)
    agents = User.query.filter(
        User.is_active == True,
        User.roles.any(Role.name == 'agent')
    ).order_by(User.full_name).all()

    warehouse = inv.get_warehouse()
    warehouse_stock = {
        item.product_id: item.quantity
        for item, product in inv.get_stock_by_location(warehouse.id)
    } if warehouse else {}

    return render_template(
        'inventory/dispatch.html',
        products=products,
        agents=agents,
        warehouse_stock=warehouse_stock,
    )


@inventory_bp.route('/return', methods=['GET', 'POST'])
@login_required
@permission_required('inventory.return')
def return_stock():
    """Agente devuelve producto al almacén."""
    if request.method == 'POST':
        agent_user_id = request.form.get('agent_user_id', type=int)
        product_id = request.form.get('product_id', type=int)
        quantity = request.form.get('quantity', type=int)
        notes = request.form.get('notes', '').strip()

        if not agent_user_id or not product_id or not quantity or quantity <= 0:
            flash('Agente, producto y cantidad son requeridos.', 'error')
        else:
            warehouse = inv.get_warehouse()
            agent_location = inv.get_agent_location(agent_user_id)

            if not agent_location:
                flash('El agente no tiene ubicación de inventario.', 'error')
            else:
                try:
                    inv.return_to_warehouse(
                        product_id=product_id,
                        quantity=quantity,
                        agent_location_id=agent_location.id,
                        warehouse_id=warehouse.id,
                        performed_by=current_user.id,
                        notes=notes or None,
                    )
                    product = ps.get_product_by_id(product_id)
                    agent = db.session.get(User, agent_user_id)
                    flash(f'{quantity}x "{product.name}" devueltos por {agent.full_name}.', 'success')
                    return redirect(url_for('inventory.index'))
                except inv.InsufficientStockError as e:
                    flash(str(e), 'error')
                except Exception as e:
                    flash(f'Error: {str(e)}', 'error')

    agents = User.query.filter(
        User.is_active == True,
        User.roles.any(Role.name == 'agent')
    ).order_by(User.full_name).all()
    products = ps.get_products_query().all()

    return render_template('inventory/return.html', products=products, agents=agents)


@inventory_bp.route('/movements')
@login_required
@permission_required('inventory.view')
def movements():
    """Historial de movimientos."""
    product_id = request.args.get('product_id', type=int)
    movement_type = request.args.get('type')

    query = inv.get_movements_query(
        product_id=product_id,
        movement_type=movement_type,
    )
    movements = query.limit(100).all()

    return render_template('inventory/movements.html', movements=movements)
