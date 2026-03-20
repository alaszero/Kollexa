"""Servicio de clientes."""
from app.extensions import db
from app.models.customer import Customer
from app.utils.audit import log_action


def create_customer(data, user_id=None):
    """Crear un nuevo cliente."""
    customer = Customer(
        full_name=data['full_name'],
        phone=data.get('phone'),
        address=data.get('address'),
        neighborhood=data.get('neighborhood'),
        city=data.get('city'),
        reference=data.get('reference'),
        gps_lat=data.get('gps_lat'),
        gps_lng=data.get('gps_lng'),
        notes=data.get('notes'),
        created_by=user_id,
    )
    db.session.add(customer)
    db.session.flush()

    log_action(
        'customer.create',
        entity_type='customer',
        entity_id=customer.id,
        new_values=customer.to_dict(),
        user_id=user_id,
    )
    db.session.commit()
    return customer


def update_customer(customer, data, user_id=None):
    """Actualizar un cliente existente."""
    old_values = customer.to_dict()
    allowed = ('full_name', 'phone', 'address', 'neighborhood', 'city',
               'reference', 'gps_lat', 'gps_lng', 'notes')

    for field in allowed:
        if field in data:
            setattr(customer, field, data[field])

    log_action(
        'customer.update',
        entity_type='customer',
        entity_id=customer.id,
        old_values=old_values,
        new_values=customer.to_dict(),
        user_id=user_id,
    )
    db.session.commit()
    return customer


def toggle_customer(customer, user_id=None):
    """Activar/desactivar cliente."""
    customer.is_active = not customer.is_active
    log_action(
        'customer.toggle',
        entity_type='customer',
        entity_id=customer.id,
        new_values={'is_active': customer.is_active},
        user_id=user_id,
    )
    db.session.commit()
    return customer


def get_customer_by_id(customer_id):
    return db.session.get(Customer, customer_id)


def get_customers_query(search=None, neighborhood=None, active_only=True):
    """Query filtrado de clientes."""
    query = Customer.query

    if active_only:
        query = query.filter_by(is_active=True)

    if search:
        like = f'%{search}%'
        query = query.filter(
            db.or_(
                Customer.full_name.ilike(like),
                Customer.phone.ilike(like),
                Customer.address.ilike(like),
            )
        )

    if neighborhood:
        query = query.filter_by(neighborhood=neighborhood)

    return query.order_by(Customer.full_name)


def get_neighborhoods():
    """Lista de colonias únicas."""
    results = db.session.query(Customer.neighborhood).filter(
        Customer.neighborhood.isnot(None),
        Customer.is_active == True,
    ).distinct().order_by(Customer.neighborhood).all()
    return [r[0] for r in results if r[0]]
