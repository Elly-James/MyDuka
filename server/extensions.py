from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flask_caching import Cache
from flask_socketio import SocketIO
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Initialize extensions
db = SQLAlchemy()
jwt = JWTManager()
mail = Mail()
migrate = Migrate()

# SocketIO configuration with eventlet for WebSocket support
socketio = SocketIO(async_mode='eventlet', logger=True, engineio_logger=True)

# Cache configuration with fallback to SimpleCache
cache = Cache(config={
    'CACHE_TYPE': 'RedisCache',
    'CACHE_REDIS_URL': None,  # Set in app config
    'CACHE_DEFAULT_TIMEOUT': 3600,
    'CACHE_TYPE_FALLBACK': 'SimpleCache'
})

# Rate limiting configuration
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "100 per hour"],
    storage_uri='memory://'
)