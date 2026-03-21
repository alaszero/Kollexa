"""Vistas web de gestion de usuarios."""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.services import auth_service as auth
from app.models.user import User, Role
from app.utils.decorators import permission_required
from app.extensions import db

users_bp = Blueprint('users', __name__, url_prefix='/users')


@users_bp.route('/')
@login_required
@permission_required('users.view')
def index():
    """Listado de usuarios."""
    role_filter = request.args.get('role', '')
    search = request.args.get('search', '').strip()

    query = User.query
    if role_filter:
        query = query.filter(User.roles.any(Role.name == role_filter))
    if search:
        like = f'%{search}%'
        query = query.filter(
            db.or_(
                User.username.ilike(like),
                User.full_name.ilike(like),
                User.email.ilike(like),
            )
        )
    users = query.order_by(User.full_name).all()
    # Filter in Python for is_active (UserMixin property issue)
    roles = Role.query.order_by(Role.name).all()

    return render_template(
        'users/index.html',
        users=users,
        roles=roles,
        role_filter=role_filter,
        search=search,
    )


@users_bp.route('/new', methods=['GET', 'POST'])
@login_required
@permission_required('users.create')
def create():
    """Crear nuevo usuario."""
    if request.method == 'POST':
        data = {
            'username': request.form.get('username', '').strip(),
            'password': request.form.get('password', ''),
            'email': request.form.get('email', '').strip() or None,
            'full_name': request.form.get('full_name', '').strip(),
            'phone': request.form.get('phone', '').strip() or None,
        }
        role_name = request.form.get('role', 'agent')

        if not data['username'] or not data['password'] or not data['full_name']:
            flash('Usuario, contrasena y nombre completo son requeridos.', 'error')
            roles = Role.query.order_by(Role.name).all()
            return render_template('users/form.html', user=None, data=data, roles=roles)

        try:
            user = auth.create_user(
                username=data['username'],
                password=data['password'],
                email=data['email'],
                full_name=data['full_name'],
                phone=data['phone'],
                role_name=role_name,
            )
            flash(f'Usuario "{user.username}" creado.', 'success')
            return redirect(url_for('users.index'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')

    roles = Role.query.order_by(Role.name).all()
    return render_template('users/form.html', user=None, data={}, roles=roles)


@users_bp.route('/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('users.edit')
def edit(user_id):
    """Editar usuario existente."""
    user = db.session.get(User, user_id)
    if not user:
        flash('Usuario no encontrado.', 'error')
        return redirect(url_for('users.index'))

    # Solo superadmin/support puede editar superadmin/support
    target_roles = [r.name for r in user.roles]
    if ('superadmin' in target_roles or 'support' in target_roles):
        if not (current_user.has_role('superadmin') or current_user.has_role('support')):
            flash('No tienes permiso para editar este usuario.', 'error')
            return redirect(url_for('users.index'))

    if request.method == 'POST':
        data = {
            'email': request.form.get('email', '').strip() or None,
            'full_name': request.form.get('full_name', '').strip(),
            'phone': request.form.get('phone', '').strip() or None,
        }
        new_password = request.form.get('password', '').strip()
        new_role = request.form.get('role', '')

        if not data['full_name']:
            flash('Nombre completo es requerido.', 'error')
            roles = Role.query.order_by(Role.name).all()
            return render_template('users/form.html', user=user, data=data, roles=roles)

        try:
            auth.update_user(user, data)

            if new_password:
                user.set_password(new_password)

            if new_role and new_role != (user.roles[0].name if user.roles else ''):
                role = Role.query.filter_by(name=new_role).first()
                if role:
                    user.roles = [role]

            db.session.commit()
            flash(f'Usuario "{user.username}" actualizado.', 'success')
            return redirect(url_for('users.index'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')

    roles = Role.query.order_by(Role.name).all()
    return render_template('users/form.html', user=user, data={}, roles=roles)


@users_bp.route('/<int:user_id>/toggle', methods=['POST'])
@login_required
@permission_required('users.edit')
def toggle(user_id):
    """Activar/desactivar usuario."""
    user = db.session.get(User, user_id)
    if not user:
        flash('Usuario no encontrado.', 'error')
        return redirect(url_for('users.index'))

    if user.id == current_user.id:
        flash('No puedes desactivarte a ti mismo.', 'error')
        return redirect(url_for('users.index'))

    user.is_active = not user.is_active
    db.session.commit()
    state = 'activado' if user.is_active else 'desactivado'
    flash(f'Usuario "{user.username}" {state}.', 'info')
    return redirect(url_for('users.index'))


@users_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Cambiar contrasena propia."""
    if request.method == 'POST':
        current_pw = request.form.get('current_password', '')
        new_pw = request.form.get('new_password', '')
        confirm_pw = request.form.get('confirm_password', '')

        if not current_user.check_password(current_pw):
            flash('Contrasena actual incorrecta.', 'error')
        elif not new_pw or len(new_pw) < 6:
            flash('La nueva contrasena debe tener al menos 6 caracteres.', 'error')
        elif new_pw != confirm_pw:
            flash('Las contrasenas no coinciden.', 'error')
        else:
            current_user.set_password(new_pw)
            db.session.commit()
            flash('Contrasena actualizada.', 'success')
            return redirect(url_for('web.dashboard'))

    return render_template('users/change_password.html')
