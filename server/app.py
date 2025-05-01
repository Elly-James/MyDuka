# app.py
import logging
from flask import Flask, jsonify, abort
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db, jwt, cache, socketio, cors, limiter, migrate, mail
from config import config
from models import User

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app(config_name='development'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    try:
        db.init_app(app)
        jwt.init_app(app)
        mail.init_app(app)
        cache.init_app(app)
        migrate.init_app(app, db)
        cors.init_app(app, resources={r"/api/*": {"origins": app.config.get('CORS_ORIGINS', '*')}})
        limiter.init_app(app)
        
        # Initialize SocketIO only if not in testing mode
        if config_name != 'testing':
            socketio.init_app(
                app,
                async_mode='eventlet',
                cors_allowed_origins=app.config.get('CORS_ORIGINS', '*'),
                logger=True,
                engineio_logger=True
            )
    except Exception as e:
        logger.error(f"Failed to initialize extensions: {str(e)}")
        raise
    
    # Register blueprints
    from routes.auth import auth_bp
    from routes.inventory import inventory_bp
    from routes.users import users_bp
    from routes.reports import reports_bp
    from routes.notifications import notifications_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(inventory_bp, url_prefix='/api/inventory')
    app.register_blueprint(users_bp, url_prefix='/api/users')
    app.register_blueprint(reports_bp, url_prefix='/api/reports')
    app.register_blueprint(notifications_bp, url_prefix='/api/notifications')
    
    # Role-based dashboard routes
    @app.route('/merchant-dashboard')
    @jwt_required()
    def merchant_dashboard():
        if get_jwt_identity()['role'] != 'MERCHANT':
            abort(403, description="Merchant role required")
        return jsonify({"message": "Merchant dashboard"})
    
    @app.route('/admin-dashboard')
    @jwt_required()
    def admin_dashboard():
        if get_jwt_identity()['role'] != 'ADMIN':
            abort(403, description="Admin role required")
        return jsonify({"message": "Admin dashboard"})
    
    @app.route('/clerk-dashboard')
    @jwt_required()
    def clerk_dashboard():
        if get_jwt_identity()['role'] != 'CLERK':
            abort(403, description="Clerk role required")
        return jsonify({"message": "Clerk dashboard"})
    
    # Health check endpoint
    @app.route('/health')
    def health():
        try:
            db.session.execute('SELECT 1')
            return jsonify({"status": "healthy", "database": "connected"})
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return jsonify({"status": "unhealthy", "database": "disconnected"}), 500
    
    # Custom error handlers
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"status": "error", "message": str(error.description)}), 400
    
    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({"status": "error", "message": str(error.description or "Forbidden")}), 403
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"status": "error", "message": str(error.description or "Resource not found")}), 404
    
    @app.errorhandler(429)
    def too_many_requests(error):
        return jsonify({"status": "error", "message": "Rate limit exceeded"}), 429
    
    # JWT user loader
    @jwt.user_identity_loader
    def user_identity_lookup(user):
        return {
            'id': user.id,
            'role': user.role.name,
            'store_id': user.store_id
        }

    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        identity = jwt_data["sub"]
        return User.query.get(identity["id"])
    
    logger.info(f"Application started with config: {config_name}")
    return app

app = create_app()

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, use_reloader=False)