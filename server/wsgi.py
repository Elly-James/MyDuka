import os
import json

# Patch gevent FIRST before anything else
from gevent import monkey
monkey.patch_all()

# Now patch get_jwt_identity globally BEFORE any blueprints are imported
# This ensures all route files get the patched version
import flask_jwt_extended as _jwt_ext
_original_get_jwt_identity = _jwt_ext.get_jwt_identity

def _patched_get_jwt_identity():
    """
    Returns JWT identity as a dict always.
    Flask-JWT-Extended 4.x stores the subject as a JSON string;
    this patch deserializes it transparently for all route files.
    """
    raw = _original_get_jwt_identity()
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            return raw
    return raw

# Patch at module level so ALL imports of get_jwt_identity get the fixed version
_jwt_ext.get_jwt_identity = _patched_get_jwt_identity

# Also patch the commonly used direct import path
import sys
# Pre-create a fake module entry so `from flask_jwt_extended import get_jwt_identity`
# in any blueprint gets our patched version
_jwt_ext_module = sys.modules.get('flask_jwt_extended')
if _jwt_ext_module:
    _jwt_ext_module.get_jwt_identity = _patched_get_jwt_identity

from app import create_app, socketio

app = create_app(os.getenv('FLASK_ENV', 'production'))

if __name__ == '__main__':
    socketio.run(app)