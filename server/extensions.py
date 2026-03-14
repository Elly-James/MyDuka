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

# SocketIO — switched from eventlet to gevent for Python 3.11+ compatibility on Render
socketio = SocketIO(async_mode='gevent', logger=True, engineio_logger=True)

# Cache — initialized without config here; config is applied in create_app()
# Will use SimpleCache by default, RedisCache if CACHE_REDIS_URL is set in env
cache = Cache()

# Rate limiting — uses in-memory storage (sufficient for single-worker Render free tier)
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "100 per hour"],
    storage_uri='memory://'
)