"""Seed de datos de demostración: 30 productos, 10 agentes, 200 clientes, ventas y pagos."""
import random
from datetime import date, timedelta
from decimal import Decimal

# Reproducible
random.seed(42)


# ──────────────────────────────────────────────
# Catálogos realistas
# ──────────────────────────────────────────────

PRODUCTS = [
    # (nombre, sku, costo, venta, categoría)
    ('Sartén Antiadherente 26cm', 'SAR-026', 120, 299, 'Cocina'),
    ('Sartén Antiadherente 30cm', 'SAR-030', 150, 349, 'Cocina'),
    ('Juego de Ollas 5 piezas', 'OLL-005', 380, 899, 'Cocina'),
    ('Olla Express 6L', 'OEX-006', 450, 1099, 'Cocina'),
    ('Licuadora 3 velocidades', 'LIC-003', 280, 649, 'Electrodomésticos'),
    ('Plancha de Vapor', 'PLA-VAP', 220, 499, 'Electrodomésticos'),
    ('Batidora de Mano', 'BAT-MAN', 180, 399, 'Electrodomésticos'),
    ('Sandwichera Doble', 'SAN-DOB', 150, 349, 'Electrodomésticos'),
    ('Cafetera 12 Tazas', 'CAF-012', 320, 749, 'Electrodomésticos'),
    ('Ventilador de Pedestal', 'VEN-PED', 280, 649, 'Hogar'),
    ('Cobija Térmica Individual', 'COB-IND', 180, 449, 'Hogar'),
    ('Cobija Térmica Matrimonial', 'COB-MAT', 250, 599, 'Hogar'),
    ('Edredón King Size', 'EDR-KIN', 400, 999, 'Hogar'),
    ('Juego de Sábanas Matrimonial', 'SAB-MAT', 160, 399, 'Hogar'),
    ('Almohada Memory Foam', 'ALM-MEM', 120, 299, 'Hogar'),
    ('Juego de Toallas 6 piezas', 'TOA-006', 140, 349, 'Hogar'),
    ('Cortinas Blackout 2 paneles', 'COR-BLA', 200, 499, 'Hogar'),
    ('Tapete Decorativo', 'TAP-DEC', 160, 399, 'Hogar'),
    ('Juego de Vasos 12 piezas', 'VAS-012', 90, 229, 'Cocina'),
    ('Juego de Platos 20 piezas', 'PLA-020', 200, 499, 'Cocina'),
    ('Juego de Cubiertos 24 piezas', 'CUB-024', 120, 299, 'Cocina'),
    ('Tabla de Planchar', 'TAB-PLA', 180, 449, 'Hogar'),
    ('Organizador de Closet', 'ORG-CLO', 140, 349, 'Hogar'),
    ('Set de Cuchillos 6 piezas', 'CUC-006', 160, 399, 'Cocina'),
    ('Horno Eléctrico 20L', 'HOR-020', 480, 1149, 'Electrodomésticos'),
    ('Parrilla Eléctrica', 'PAR-ELE', 350, 849, 'Electrodomésticos'),
    ('Aspiradora de Mano', 'ASP-MAN', 300, 699, 'Electrodomésticos'),
    ('Báscula Digital', 'BAS-DIG', 80, 199, 'Hogar'),
    ('Reloj de Pared', 'REL-PAR', 60, 149, 'Hogar'),
    ('Lámpara de Escritorio LED', 'LAM-LED', 100, 249, 'Hogar'),
]

AGENTS = [
    # (username, nombre, teléfono)
    ('pedro_v', 'Pedro Velázquez', '55 2001 1001'),
    ('maria_l', 'María López Hernández', '55 2001 1002'),
    ('carlos_r', 'Carlos Ramírez Soto', '55 2001 1003'),
    ('ana_g', 'Ana García Mendoza', '55 2001 1004'),
    ('luis_m', 'Luis Martínez Díaz', '55 2001 1005'),
    ('rosa_p', 'Rosa Pérez Flores', '55 2001 1006'),
    ('jorge_s', 'Jorge Sánchez Ortiz', '55 2001 1007'),
    ('elena_c', 'Elena Cruz Vega', '55 2001 1008'),
    ('miguel_h', 'Miguel Hernández Luna', '55 2001 1009'),
    ('sofia_t', 'Sofía Torres Reyes', '55 2001 1010'),
]

NEIGHBORHOODS = [
    'Centro', 'La Esperanza', 'San Miguel', 'Las Flores', 'El Rosario',
    'Lomas del Valle', 'Santa Fe', 'Jardines', 'Industrial', 'Reforma',
    'La Paz', 'San Juan', 'Morelos', 'Juárez', 'Independencia',
]

CITIES = ['CDMX', 'Ecatepec', 'Neza', 'Tlalnepantla', 'Naucalpan']

FIRST_NAMES_M = [
    'Juan', 'José', 'Antonio', 'Francisco', 'Roberto', 'Manuel', 'Alejandro',
    'Ricardo', 'Eduardo', 'Fernando', 'Raúl', 'Arturo', 'Oscar', 'Enrique',
    'Gerardo', 'Martín', 'Hugo', 'Daniel', 'Sergio', 'Héctor',
]
FIRST_NAMES_F = [
    'María', 'Guadalupe', 'Patricia', 'Rosa', 'Laura', 'Carmen', 'Sandra',
    'Leticia', 'Adriana', 'Verónica', 'Silvia', 'Claudia', 'Gabriela',
    'Teresa', 'Martha', 'Norma', 'Beatriz', 'Lucía', 'Irma', 'Gloria',
]
LAST_NAMES = [
    'García', 'Hernández', 'López', 'Martínez', 'González', 'Rodríguez',
    'Pérez', 'Sánchez', 'Ramírez', 'Torres', 'Flores', 'Rivera',
    'Gómez', 'Díaz', 'Cruz', 'Morales', 'Reyes', 'Ortiz', 'Gutiérrez', 'Ruiz',
]

STREETS = [
    'Av. Hidalgo', 'Calle Morelos', 'Av. Juárez', 'Calle 5 de Mayo', 'Av. Reforma',
    'Calle Independencia', 'Av. Insurgentes', 'Calle Allende', 'Calle Guerrero',
    'Av. Universidad', 'Calle Madero', 'Av. Revolución', 'Calle Aldama',
    'Calle Bravo', 'Av. Constitución', 'Calle Victoria', 'Calle Libertad',
]


def _random_name():
    if random.random() < 0.5:
        first = random.choice(FIRST_NAMES_M)
    else:
        first = random.choice(FIRST_NAMES_F)
    return f'{first} {random.choice(LAST_NAMES)} {random.choice(LAST_NAMES)}'


def _random_phone():
    return f'55 {random.randint(1000,9999)} {random.randint(1000,9999)}'


def _random_address():
    street = random.choice(STREETS)
    num = random.randint(1, 500)
    return f'{street} #{num}'


def run_demo_seed(app):
    """Ejecutar seed de datos demo."""
    with app.app_context():
        from app.extensions import db
        from app.services.auth_service import create_user
        from app.services.product_service import create_product
        from app.services.customer_service import create_customer
        from app.services import inventory_service as inv
        from app.services import sale_service as ss
        from app.services import collection_service as col
        from app.models.user import User

        print('=== SEED DE DATOS DEMO ===')
        print()

        # ── 1. Productos ──
        print('Creando 30 productos...')
        product_ids = []
        for name, sku, cost, price, category in PRODUCTS:
            p = create_product({
                'name': name, 'sku': sku,
                'base_price': str(cost), 'sell_price': str(price),
                'category': category,
            }, user_id=1)
            product_ids.append(p.id)
        print(f'  {len(product_ids)} productos creados.')

        # ── 2. Agentes ──
        print('Creando 10 agentes...')
        agent_ids = []
        for username, full_name, phone in AGENTS:
            # Verificar si ya existe
            existing = User.query.filter_by(username=username).first()
            if existing:
                agent_ids.append(existing.id)
                continue
            agent = create_user(
                username=username,
                password='agent123',
                full_name=full_name,
                phone=phone,
                role_names=['agent'],
            )
            agent_ids.append(agent.id)
        print(f'  {len(agent_ids)} agentes creados.')

        # ── 3. Surtir agentes ──
        print('Surtiendo agentes desde almacén...')
        warehouse = inv.get_warehouse()

        # Primero, meter stock al almacén
        for pid in product_ids:
            inv.purchase_stock(
                product_id=pid,
                quantity=random.randint(80, 200),
                warehouse_id=warehouse.id,
                performed_by=1,
                notes='Stock inicial demo',
            )

        # Despachar a cada agente
        for agent_id in agent_ids:
            agent_loc = inv.get_agent_location(agent_id)
            if not agent_loc:
                continue
            # Cada agente recibe entre 8 y 15 productos distintos
            agent_products = random.sample(product_ids, random.randint(8, 15))
            for pid in agent_products:
                qty = random.randint(3, 12)
                try:
                    inv.dispatch_to_agent(
                        product_id=pid,
                        quantity=qty,
                        warehouse_id=warehouse.id,
                        agent_location_id=agent_loc.id,
                        performed_by=1,
                    )
                except Exception:
                    pass  # Si no hay suficiente stock, skip
        print('  Agentes surtidos.')

        # ── 4. Clientes ──
        print('Creando 200 clientes...')
        customer_ids = []
        for i in range(200):
            # Distribuir clientes entre agentes
            agent_id = random.choice(agent_ids)
            c = create_customer({
                'full_name': _random_name(),
                'phone': _random_phone(),
                'address': _random_address(),
                'neighborhood': random.choice(NEIGHBORHOODS),
                'city': random.choice(CITIES),
                'reference': random.choice([
                    'Casa azul con portón negro',
                    'Frente a la tienda de abarrotes',
                    'Junto a la farmacia',
                    'Esquina con la panadería',
                    'Casa de dos pisos con barda blanca',
                    'A media cuadra del parque',
                    'Junto a la escuela primaria',
                    None,
                ]),
            }, user_id=agent_id)
            customer_ids.append((c.id, agent_id))
        print(f'  {len(customer_ids)} clientes creados.')

        # ── 5. Ventas ──
        print('Creando ventas...')
        today = date.today()
        sale_count = 0
        sale_ids = []

        for cust_id, agent_id in customer_ids:
            # 70% de clientes tienen al menos 1 venta
            if random.random() > 0.70:
                continue

            agent_loc = inv.get_agent_location(agent_id)
            if not agent_loc:
                continue

            # Obtener stock del agente
            agent_items = inv.get_stock_by_location(agent_loc.id)
            if not agent_items:
                continue

            # 1-3 productos por venta
            num_items = min(random.randint(1, 3), len(agent_items))
            selected = random.sample(agent_items, num_items)

            items = []
            for stock_item, product in selected:
                qty = min(random.randint(1, 2), stock_item.quantity)
                if qty > 0:
                    items.append({
                        'product_id': product.id,
                        'quantity': qty,
                    })

            if not items:
                continue

            num_installments = random.choice([4, 5, 6, 8, 10, 12])

            # Ventas en las últimas 8 semanas
            sale_days_ago = random.randint(0, 56)
            start_date = today - timedelta(days=sale_days_ago) + timedelta(days=7)

            try:
                sale = ss.create_sale(
                    data={
                        'customer_id': cust_id,
                        'items': items,
                        'num_installments': num_installments,
                        'start_date': start_date.isoformat(),
                    },
                    agent_id=agent_id,
                )
                sale_count += 1
                sale_ids.append((sale.id, agent_id, sale_days_ago))
            except Exception:
                continue

        print(f'  {sale_count} ventas creadas.')

        # ── 6. Pagos ──
        print('Simulando pagos...')
        payment_count = 0

        for sale_id, agent_id, days_ago in sale_ids:
            sale = ss.get_sale_full(sale_id)
            if not sale or not sale.payment_plan:
                continue

            installments = sale.payment_plan.installments

            for inst in installments:
                # Si la cuota ya venció, 75% de chance de estar pagada
                if inst.due_date <= today:
                    if random.random() < 0.75:
                        try:
                            owed = inst.expected_amount - inst.paid_amount
                            if owed > 0:
                                col.collect_payment(
                                    installment_id=inst.id,
                                    amount=str(owed),
                                    collected_by=agent_id,
                                    payment_method=random.choice(['cash', 'cash', 'cash', 'transfer']),
                                )
                                payment_count += 1
                        except Exception:
                            continue
                    elif random.random() < 0.3:
                        # Pago parcial
                        try:
                            partial = Decimal(str(round(float(inst.expected_amount) * random.uniform(0.3, 0.7), 2)))
                            if partial > 0 and inst.paid_amount == 0:
                                col.collect_payment(
                                    installment_id=inst.id,
                                    amount=str(partial),
                                    collected_by=agent_id,
                                    payment_method='cash',
                                )
                                payment_count += 1
                        except Exception:
                            continue

        # Actualizar estados de cuotas vencidas
        col.update_overdue_statuses()

        print(f'  {payment_count} pagos registrados.')

        # ── Resumen ──
        print()
        print('=== RESUMEN DEMO ===')
        print(f'Productos:  {len(product_ids)}')
        print(f'Agentes:    {len(agent_ids)}')
        print(f'Clientes:   {len(customer_ids)}')
        print(f'Ventas:     {sale_count}')
        print(f'Pagos:      {payment_count}')

        stats = col.get_collection_stats(view_all=True)
        print(f'Pendiente:  ${stats["pending_total"]}')
        print(f'Atrasadas:  {stats["overdue_count"]}')
        print()
        print('Credenciales:')
        print('  Admin:    admin / admin123')
        print('  Agentes:  pedro_v, maria_l, carlos_r... / agent123')
        print()
        print('SEED DEMO COMPLETADO')


if __name__ == '__main__':
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from app import create_app
    app = create_app('development')
    run_demo_seed(app)
