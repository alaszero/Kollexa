"""Seed: datos iniciales del sistema (roles, permisos, superadmin, config, almacén)."""
import os
from app.extensions import db
from app.models.user import User, Role, Permission
from app.models.inventory import StockLocation
from app.models.system import SystemConfig, SystemVersion


# ──────────────────────────────────────────────
# Catálogo de permisos por módulo
# ──────────────────────────────────────────────
PERMISSIONS = [
    # Usuarios
    ('users.view', 'users', 'Ver usuarios'),
    ('users.create', 'users', 'Crear usuarios'),
    ('users.edit', 'users', 'Editar usuarios'),
    ('users.toggle', 'users', 'Activar/desactivar usuarios'),

    # Roles
    ('roles.view', 'roles', 'Ver roles'),
    ('roles.manage', 'roles', 'Gestionar roles y permisos'),

    # Clientes
    ('customers.view', 'customers', 'Ver clientes'),
    ('customers.create', 'customers', 'Crear clientes'),
    ('customers.edit', 'customers', 'Editar clientes'),

    # Productos
    ('products.view', 'products', 'Ver productos'),
    ('products.create', 'products', 'Crear productos'),
    ('products.edit', 'products', 'Editar productos'),

    # Inventario
    ('inventory.view', 'inventory', 'Ver inventario'),
    ('inventory.purchase', 'inventory', 'Registrar compras/entradas'),
    ('inventory.dispatch', 'inventory', 'Surtir agentes desde almacén'),
    ('inventory.return', 'inventory', 'Registrar devoluciones a almacén'),
    ('inventory.adjust', 'inventory', 'Hacer ajustes de inventario'),
    ('inventory.reconcile', 'inventory', 'Conciliar inventario'),
    ('inventory.view_agent_stock', 'inventory', 'Ver stock de agentes'),

    # Ventas
    ('sales.view', 'sales', 'Ver ventas'),
    ('sales.create', 'sales', 'Crear ventas'),
    ('sales.cancel', 'sales', 'Cancelar ventas'),
    ('sales.view_all', 'sales', 'Ver ventas de todos los agentes'),

    # Cobranza
    ('collections.view', 'collections', 'Ver cobranza'),
    ('collections.collect', 'collections', 'Registrar pagos'),
    ('collections.view_all', 'collections', 'Ver cobranza de todos'),

    # Dashboard
    ('dashboard.view', 'dashboard', 'Ver dashboard'),
    ('dashboard.reports', 'dashboard', 'Ver reportes completos'),

    # Configuración
    ('config.view', 'config', 'Ver configuración del sistema'),
    ('config.edit', 'config', 'Modificar configuración del sistema'),

    # Auditoría
    ('audit.view', 'audit', 'Ver log de auditoría'),
]


# ──────────────────────────────────────────────
# Roles del sistema con sus permisos
# ──────────────────────────────────────────────
SYSTEM_ROLES = {
    'superadmin': {
        'description': 'Acceso total al sistema',
        'permissions': '__all__',  # Superadmin tiene todos
    },
    'admin': {
        'description': 'Administrador del negocio',
        'permissions': [
            'users.view', 'users.create', 'users.edit', 'users.toggle',
            'roles.view',
            'customers.view', 'customers.create', 'customers.edit',
            'products.view', 'products.create', 'products.edit',
            'inventory.view', 'inventory.purchase', 'inventory.dispatch',
            'inventory.return', 'inventory.adjust', 'inventory.reconcile',
            'inventory.view_agent_stock',
            'sales.view', 'sales.create', 'sales.cancel', 'sales.view_all',
            'collections.view', 'collections.collect', 'collections.view_all',
            'dashboard.view', 'dashboard.reports',
            'config.view',
        ],
    },
    'agent': {
        'description': 'Agente de ventas/cobranza en campo',
        'permissions': [
            'customers.view', 'customers.create', 'customers.edit',
            'products.view',
            'inventory.view',
            'sales.view', 'sales.create',
            'collections.view', 'collections.collect',
            'dashboard.view',
        ],
    },
}


# ──────────────────────────────────────────────
# Configuraciones iniciales del sistema
# ──────────────────────────────────────────────
DEFAULT_CONFIG = [
    ('collection_mode', 'agent', 'string', 'Modo de cobranza: "agent" o "collector"'),
    ('interest_enabled', 'false', 'bool', 'Habilitar cobro de intereses'),
    ('penalty_enabled', 'false', 'bool', 'Habilitar penalizaciones por atraso'),
    ('default_interest_rate', '0', 'float', 'Tasa de interés por defecto (%)'),
    ('default_penalty_rate', '5', 'float', 'Tasa de penalización por atraso (%)'),
    ('default_grace_days', '3', 'int', 'Días de gracia antes de penalizar'),
    ('default_installments', '10', 'int', 'Número de cuotas semanales por defecto'),
    ('company_name', 'Kollexa', 'string', 'Nombre de la empresa'),
]


def run_seed(app):
    """Ejecutar seed completo."""
    with app.app_context():
        _seed_permissions()
        _seed_roles()
        _seed_default_admin()
        _seed_warehouse()
        _seed_config()
        _seed_version(app)
        db.session.commit()
        print('Seed completado exitosamente.')


def _seed_permissions():
    """Crear permisos si no existen."""
    for code, module, description in PERMISSIONS:
        existing = Permission.query.filter_by(code=code).first()
        if not existing:
            perm = Permission(code=code, module=module, description=description)
            db.session.add(perm)
            print(f'  + Permiso: {code}')
    db.session.flush()


def _seed_roles():
    """Crear roles del sistema con sus permisos."""
    all_permissions = Permission.query.all()
    perm_by_code = {p.code: p for p in all_permissions}

    for role_name, config in SYSTEM_ROLES.items():
        role = Role.query.filter_by(name=role_name).first()
        if not role:
            role = Role(
                name=role_name,
                description=config['description'],
                is_system=True,
            )
            db.session.add(role)
            print(f'  + Rol: {role_name}')

        # Asignar permisos
        if config['permissions'] == '__all__':
            role.permissions = all_permissions
        else:
            role.permissions = [
                perm_by_code[code]
                for code in config['permissions']
                if code in perm_by_code
            ]
    db.session.flush()


def _seed_default_admin():
    """Crear superadmin por defecto si no existe ningún usuario."""
    if User.query.first() is not None:
        print('  = Ya existen usuarios, se omite creación de admin.')
        return

    username = os.getenv('DEFAULT_ADMIN_USERNAME', 'admin')
    password = os.getenv('DEFAULT_ADMIN_PASSWORD', 'admin123')
    email = os.getenv('DEFAULT_ADMIN_EMAIL', 'admin@kollexa.local')

    superadmin_role = Role.query.filter_by(name='superadmin').first()

    user = User(
        username=username,
        full_name='Administrador',
        email=email,
    )
    user.set_password(password)
    user.roles = [superadmin_role]

    db.session.add(user)
    db.session.flush()
    print(f'  + Superadmin creado: {username}')


def _seed_warehouse():
    """Crear almacén principal si no existe."""
    existing = StockLocation.query.filter_by(type='warehouse').first()
    if not existing:
        warehouse = StockLocation(
            type='warehouse',
            name='Almacén Principal',
            user_id=None,
        )
        db.session.add(warehouse)
        print('  + Almacén principal creado.')


def _seed_config():
    """Crear configuraciones por defecto."""
    for key, value, value_type, description in DEFAULT_CONFIG:
        existing = SystemConfig.query.filter_by(key=key).first()
        if not existing:
            config = SystemConfig(
                key=key,
                value=value,
                value_type=value_type,
                description=description,
            )
            db.session.add(config)
            print(f'  + Config: {key} = {value}')


def _seed_version(app):
    """Registrar versión inicial."""
    version = app.config.get('VERSION', '0.1.0')
    existing = SystemVersion.query.filter_by(version=version).first()
    if not existing:
        sv = SystemVersion(
            version=version,
            build='initial',
            installed_by='seed',
            status='active',
        )
        db.session.add(sv)
        print(f'  + Versión registrada: {version}')


def create_admin_user(username, password, email):
    """Crear un usuario admin (llamado desde CLI)."""
    if User.query.filter_by(username=username).first():
        return None

    admin_role = Role.query.filter_by(name='admin').first()
    user = User(
        username=username,
        full_name=username.capitalize(),
        email=email,
    )
    user.set_password(password)
    if admin_role:
        user.roles = [admin_role]

    db.session.add(user)
    db.session.commit()
    return user
