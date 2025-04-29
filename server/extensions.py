# extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flask_caching import Cache
from flask_socketio import SocketIO
from flask_migrate import Migrate
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Initialize extensions without any model dependencies
db = SQLAlchemy()
jwt = JWTManager()
mail = Mail()  # Added for email functionality
migrate = Migrate()
cors = CORS()

# Cache configuration
cache = Cache(config={
    'CACHE_TYPE': 'RedisCache',
    'CACHE_REDIS_HOST': 'localhost',
    'CACHE_REDIS_PORT': 6379,
    'CACHE_REDIS_DB': 0,
    'CACHE_DEFAULT_TIMEOUT': 3600
})

# SocketIO configuration (initialize in app.py, not here)
socketio = SocketIO()

# Rate limiting configuration
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "100 per hour"],
    storage_uri="memory://"  # Fallback to memory for development
)