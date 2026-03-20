"""Validadores de input."""
from decimal import Decimal, InvalidOperation


def validate_required(data, *fields):
    """Validar que los campos requeridos existan y no estén vacíos.

    Returns:
        Lista de errores (vacía si todo OK)
    """
    errors = []
    for field in fields:
        value = data.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            errors.append(f'El campo "{field}" es requerido.')
    return errors


def validate_positive_decimal(value, field_name):
    """Validar que un valor sea un decimal positivo."""
    try:
        d = Decimal(str(value))
        if d <= 0:
            return f'"{field_name}" debe ser mayor a cero.'
    except (InvalidOperation, ValueError, TypeError):
        return f'"{field_name}" no es un número válido.'
    return None


def validate_positive_integer(value, field_name):
    """Validar que un valor sea un entero positivo."""
    try:
        i = int(value)
        if i <= 0:
            return f'"{field_name}" debe ser un entero mayor a cero.'
    except (ValueError, TypeError):
        return f'"{field_name}" no es un entero válido.'
    return None
