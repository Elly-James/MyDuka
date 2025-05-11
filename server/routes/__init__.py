from .auth import auth_bp
from .inventory import inventory_bp
from .users import users_bp
from .reports import reports_bp
from .notifications import notifications_bp
from .stores import stores_bp
from .dashboard import dashboard_bp

# List all blueprints to register
__all__ = [
    'auth_bp',
    'inventory_bp',
    'users_bp',
    'reports_bp',
    'notifications_bp',
    'stores_bp',
    'dashboard_bp'
]