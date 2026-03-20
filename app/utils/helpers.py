"""Utilidades generales."""
from decimal import Decimal, ROUND_HALF_UP
from flask import request


def format_currency(amount):
    """Formatear cantidad a moneda MXN."""
    if amount is None:
        return '$0.00'
    d = Decimal(str(amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return f'${d:,.2f}'


def round_currency(amount):
    """Redondear a 2 decimales para operaciones financieras."""
    return Decimal(str(amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def get_pagination_params():
    """Obtener parámetros de paginación del request."""
    from flask import current_app
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', None, type=int)

    default_size = current_app.config.get('DEFAULT_PAGE_SIZE', 25)
    max_size = current_app.config.get('MAX_PAGE_SIZE', 100)

    if per_page is None:
        per_page = default_size
    per_page = min(per_page, max_size)
    page = max(page, 1)

    return page, per_page


def paginated_response(query, page, per_page):
    """Generar respuesta paginada estándar."""
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return {
        'data': [item.to_dict() for item in pagination.items],
        'meta': {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'pages': pagination.pages,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev,
        }
    }


def get_client_ip():
    """Obtener IP del cliente (compatible con Cloudflare Tunnel)."""
    # Cloudflare envía la IP real en CF-Connecting-IP
    return (
        request.headers.get('CF-Connecting-IP')
        or request.headers.get('X-Forwarded-For', '').split(',')[0].strip()
        or request.remote_addr
    )
