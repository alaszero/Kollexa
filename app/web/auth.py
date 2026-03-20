"""Vistas web de autenticación."""
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.web import web_bp
from app.services.auth_service import authenticate_user
from app.utils.audit import log_action
from app.extensions import db


@web_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('web.dashboard'))
    return redirect(url_for('web_auth.login'))


@web_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard/index.html')


# Blueprint separado para auth (evitar conflicto de nombres)
from flask import Blueprint
web_auth_bp = Blueprint('web_auth', __name__)


@web_auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('web.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = authenticate_user(username, password)
        if user:
            login_user(user, remember=True)
            log_action('auth.login', entity_type='user', entity_id=user.id, user_id=user.id)
            db.session.commit()

            next_page = request.args.get('next')
            return redirect(next_page or url_for('web.dashboard'))

        flash('Usuario o contraseña incorrectos.', 'error')

    return render_template('auth/login.html')


@web_auth_bp.route('/logout')
@login_required
def logout():
    log_action('auth.logout', entity_type='user', entity_id=current_user.id)
    db.session.commit()
    logout_user()
    flash('Sesión cerrada.', 'info')
    return redirect(url_for('web_auth.login'))
