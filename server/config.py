
# config.py
import os
from datetime import timedelta

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'myduka-secret-key')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-key')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@myduka.com')
    INVITATION_EXPIRY = timedelta(days=7)  # Expiry for invitation links

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    print("DEBUG: DevelopmentConfig SQLALCHEMY_DATABASE_URI =", SQLALCHEMY_DATABASE_URI)  # Debug statement

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL')
    print("DEBUG: TestingConfig SQLALCHEMY_DATABASE_URI =", SQLALCHEMY_DATABASE_URI)  # Debug statement
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=5)
    WTF_CSRF_ENABLED = False

class ProductionConfig(Config):
    """Production configuration."""
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    print("DEBUG: ProductionConfig SQLALCHEMY_DATABASE_URI =", SQLALCHEMY_DATABASE_URI)  # Debug statement
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=1)

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}