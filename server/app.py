import logging
import os
from flask import Flask, jsonify, abort, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_cors import CORS
from extensions import db, cache, socketio, limiter, migrate, mail, jwt
from config import config
from models import User

# Configure root logger
logging.basicConfig(
    level=logging.ERROR if os.getenv('FLASK_ENV') == 'production' else logging.INFO,
    format='%(asctime)s %(levelname)s:%(name)s:%(message)s'
)
logger = logging.getLogger(__name__)

def create_app(config_name='development'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Database connection pooling
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 10,
        'max_overflow': 20,
        'pool_timeout': 30,
    }

    # Initialize extensions
    try:
        db.init_app(app)
        jwt.init_app(app)
        mail.init_app(app)
        cache.init_app(app)
        migrate.init_app(app, db)
        
        # Configure CORS
        cors_origins = app.config.get('CORS_ORIGINS', 'http://localhost:5173').split(',')
        CORS(app, resources={
            r"/api/*": {
                'origins': cors_origins,
                'methods': ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
                'allow_headers': ['Content-Type', 'Authorization', 'X-Requested-With'],
                'supports_credentials': True,
                'expose_headers': ['Content-Type', 'Authorization']
            }
        })
        
        # Configure Flask-Limiter
        app.config['RATELIMIT_STORAGE_URI'] = app.config.get('LIMITER_STORAGE_URI', 'memory://')
        limiter.init_app(app)
        
        # Initialize SocketIO after other extensions
        if config_name != 'testing':
            logger.info(f'Initializing SocketIO with CORS origins: {cors_origins}')
            socketio.init_app(
                app,
                async_mode='eventlet',
                cors_allowed_origins=cors_origins,
                path='/socket.io',
                ping_timeout=10,
                ping_interval=5,
                reconnection=True,
                reconnection_attempts=5,
                reconnection_delay=1000,
                reconnection_delay_max=5000,
                logger=True,
                engineio_logger=True
            )
    except Exception as e:
        logger.error(f'Failed to initialize extensions: {str(e)}')
        raise

    # Register blueprints
    from routes.auth import auth_bp
    from routes.inventory import inventory_bp
    from routes.users import users_bp
    from routes.reports import reports_bp
    from routes.notifications import notifications_bp
    from routes.stores import stores_bp
    from routes.dashboard import dashboard_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(inventory_bp, url_prefix='/api/inventory')
    app.register_blueprint(users_bp, url_prefix='/api/users')
    app.register_blueprint(reports_bp, url_prefix='/api/reports')
    app.register_blueprint(stores_bp, url_prefix='/api/stores')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    app.register_blueprint(notifications_bp, url_prefix='/api/notifications')

    # Handle OPTIONS requests for all /api/* routes
    @app.route('/api/<path:path>', methods=['OPTIONS'])
    def handle_options(path):
        logger.info(f'Handling OPTIONS request for /api/{path} from {request.remote_addr}')
        return '', 204, {
            'Access-Control-Allow-Origin': 'http://localhost:5173',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With',
            'Access-Control-Allow-Credentials': 'true'
        }

    # Middleware to log requests
    @app.before_request
    def log_request_info():
        logger.info(f'Request: {request.method} {request.url} from {request.remote_addr}')

    # Apply global rate limit to the app
    @app.after_request
    def apply_global_rate_limit(response):
        limiter.limit("500 per day;100 per hour")(lambda: None)  # Dummy callable
        return response

    # Role-guarded dashboard routes
    @app.route('/merchant-dashboard')
    @jwt_required()
    @limiter.limit("500 per day;100 per hour")
    def merchant_dashboard():
        if get_jwt_identity()['role'] != 'MERCHANT':
            abort(403, description='Merchant role required')
        return jsonify({'message': 'Merchant dashboard'})

    @app.route('/admin-dashboard')
    @jwt_required()
    @limiter.limit("500 per day;100 per hour")
    def admin_dashboard():
        if get_jwt_identity()['role'] != 'ADMIN':
            abort(403, description='Admin role required')
        return jsonify({'message': 'Admin dashboard'})

    @app.route('/clerk-dashboard')
    @jwt_required()
    @limiter.limit("500 per day;100 per hour")
    def clerk_dashboard():
        if get_jwt_identity()['role'] != 'CLERK':
            abort(403, description='Clerk role required')
        return jsonify({'message': 'Clerk dashboard'})

    # Health check
    @app.route('/health')
    @limiter.exempt
    def health():
        try:
            db.session.execute('SELECT 1')
            return jsonify({'status': 'healthy', 'database': 'connected'})
        except Exception as e:
            logger.error(f'Health check failed: {str(e)}')
            return jsonify({'status': 'unhealthy', 'database': 'disconnected'}), 500

    # Error handlers
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({'status': 'error', 'message': error.description or 'Bad request'}), 400

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({'status': 'error', 'message': error.description or 'Forbidden'}), 403

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'status': 'error', 'message': error.description or 'Not found'}), 404

    @app.errorhandler(422)
    def unprocessable_entity(error):
        return jsonify({'status': 'error', 'message': error.description or 'Unprocessable entity'}), 422

    @app.errorhandler(429)
    def too_many_requests(error):
        return jsonify({'status': 'error', 'message': 'Rate limit exceeded'}), 429

    # JWT error handler
    @app.errorhandler(Exception)
    def handle_jwt_error(error):
        if 'JWT' in str(error) or 'token' in str(error).lower():
            logger.error(f'JWT Error: {str(error)}')
            return jsonify({'status': 'error', 'message': 'Invalid or missing token'}), 401
        logger.error(f'Unhandled Exception: {str(error)}')
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

    # JWT callbacks
    @jwt.user_identity_loader
    def user_identity_lookup(user):
        return {
            'id': user.id,
            'role': user.role.name,
            'store_id': None  # Store ID not used since user_store handles associations
        }

    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        identity = jwt_data['sub']
        return db.session.query(User).get(identity['id'])

    # WebSocket event handlers
    @socketio.on('connect')
    def handle_connect():
        logger.info(f"WebSocket connected: {request.sid}")

    @socketio.on('disconnect')
    def handle_disconnect():
        logger.info(f"WebSocket disconnected: {request.sid}")

    @socketio.on_error_default
    def handle_socket_error(e):
        logger.error(f"WebSocket error: {str(e)}")

    # Initialize database tables
    with app.app_context():
        db.create_all()

    logger.info(f'Application started with config: {config_name}')
    return app

if __name__ == '__main__':
    app = create_app()
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, use_reloader=False)