"""Importación centralizada de todos los modelos."""
from app.models.user import User, Role, Permission, user_roles, role_permissions
from app.models.customer import Customer, CustomerPortalToken
from app.models.product import Product
from app.models.inventory import StockLocation, StockItem, InventoryMovement
from app.models.sale import Sale, SaleDetail
from app.models.payment import PaymentPlan, PaymentInstallment, Payment
from app.models.system import SystemConfig, AuditLog, SystemVersion

__all__ = [
    'User', 'Role', 'Permission', 'user_roles', 'role_permissions',
    'Customer', 'CustomerPortalToken',
    'Product',
    'StockLocation', 'StockItem', 'InventoryMovement',
    'Sale', 'SaleDetail',
    'PaymentPlan', 'PaymentInstallment', 'Payment',
    'SystemConfig', 'AuditLog', 'SystemVersion',
]
