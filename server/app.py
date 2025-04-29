# app.py
from flask import Flask, jsonify, abort
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db, jwt, cache, socketio, cors, limiter, migrate, mail  # Add mail
from config import config
import logging
from models import User  # Import User for JWT user loader

def create_app(config_name='development'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    try:
        db.init_app(app)
    except Exception as e:
        app.logger.error(f"Failed to initialize database: {str(e)}")
        raise
    
    jwt.init_app(app)
    mail.init_app(app)  # Initialize Flask-Mail
    cache.init_app(app)
    migrate.init_app(app, db)
    
    # Configure CORS and rate limiting
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})
    limiter.init_app(app)
    
    # Only initialize SocketIO if not in testing mode
    if config_name != 'testing':
        socketio.init_app(
            app,
            async_mode='eventlet',
            cors_allowed_origins="*",
            logger=True,
            engineio_logger=True
        )
    
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
            abort(403)
        return jsonify({"message": "Merchant dashboard"})
    
    @app.route('/admin-dashboard')
    @jwt_required()
    def admin_dashboard():
        if get_jwt_identity()['role'] != 'ADMIN':
            abort(403)
        return jsonify({"message": "Admin dashboard"})
    
    @app.route('/clerk-dashboard')
    @jwt_required()
    def clerk_dashboard():
        if get_jwt_identity()['role'] != 'CLERK':
            abort(403)
        return jsonify({"message": "Clerk dashboard"})
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Initialize JWT user loader
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
    
    return app

app = create_app()

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, use_reloader=False)