import os
from flask import Flask, jsonify
from extensions import db, migrate, jwt, mail, cors
from config import config

def create_app(config_name=None):
    """Application factory function"""
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    mail.init_app(app)
    cors.init_app(app)
    
    # Register routes
    from routes import auth_bp, inventory_bp, users_bp, reports_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(inventory_bp, url_prefix='/api/inventory')
    app.register_blueprint(users_bp, url_prefix='/api/users')
    app.register_blueprint(reports_bp, url_prefix='/api/reports')
    
    # JWT error handlers
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({
            'status': 'error',
            'message': 'Token has expired'
        }), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({
            'status': 'error',
            'message': 'Invalid token'
        }), 401
    
    @jwt.unauthorized_loader
    def unauthorized_callback(error):
        return jsonify({
            'status': 'error',
            'message': 'Missing authorization token'
        }), 401
    
    @app.route('/api/health')
    def health_check():
        return jsonify({'status': 'ok', 'message': 'MyDuka API is running'})
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000)