"""Helper para registrar auditoría."""
import json
from app.extensions import db
from app.models.system import AuditLog
from app.utils.helpers import get_client_ip


def log_action(action, entity_type=None, entity_id=None,
               old_values=None, new_values=None, user_id=None):
    """Registrar una acción en el log de auditoría.

    Args:
        action: Código de acción, ej: 'sale.create', 'payment.collect'
        entity_type: Tipo de entidad afectada, ej: 'sale', 'payment'
        entity_id: ID de la entidad
        old_values: Dict con valores anteriores (se serializa a JSON)
        new_values: Dict con valores nuevos (se serializa a JSON)
        user_id: ID del usuario. Si es None, intenta obtenerlo del contexto.
    """
    if user_id is None:
        try:
            from flask_login import current_user
            if current_user and current_user.is_authenticated:
                user_id = current_user.id
        except RuntimeError:
            pass  # Fuera de contexto de request

    try:
        ip = get_client_ip()
    except RuntimeError:
        ip = None

    entry = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_values=json.dumps(old_values) if old_values else None,
        new_values=json.dumps(new_values) if new_values else None,
        ip_address=ip,
    )
    db.session.add(entry)
    # No hacemos commit aquí — se commitea con la transacción principal
