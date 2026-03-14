import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY') or 'your-secret-key'

    # Fix Render's postgres:// prefix — SQLAlchemy requires postgresql://
    raw_db_url = os.getenv('DATABASE_URL')
    if not raw_db_url:
        raise ValueError("DATABASE_URL environment variable is not set")
    SQLALCHEMY_DATABASE_URI = raw_db_url.replace('postgres://', 'postgresql://', 1)

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY') or 'your-jwt-secret-key'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', os.getenv('MAIL_USERNAME', 'noreply@myduka.com'))
    INVITATION_EXPIRY = timedelta(days=int(os.getenv('INVITATION_EXPIRY_DAYS', 7)))
    LIMITER_STORAGE_URI = os.getenv('LIMITER_STORAGE_URI', 'memory://')
    CACHE_REDIS_URL = os.getenv('CACHE_REDIS_URL', None)
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:5000/api/auth/google/callback')
    SOCKETIO_MESSAGE_QUEUE = os.getenv('SOCKETIO_MESSAGE_QUEUE', None)
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:5173')
    SOCKETIO_CORS_ORIGINS = os.getenv('SOCKETIO_CORS_ORIGINS', 'http://localhost:5173')


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = True
    CORS_ORIGINS = 'http://localhost:5173'
    SOCKETIO_CORS_ORIGINS = 'http://localhost:5173'


class TestingConfig(Config):
    TESTING = True
    _test_db_url = os.getenv('TEST_DATABASE_URL')
    if not _test_db_url:
        raise ValueError("TEST_DATABASE_URL environment variable is not set")
    SQLALCHEMY_DATABASE_URI = _test_db_url.replace('postgres://', 'postgresql://', 1)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=5)
    WTF_CSRF_ENABLED = False
    CORS_ORIGINS = 'http://localhost:5173'
    SOCKETIO_CORS_ORIGINS = 'http://localhost:5173'


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_ECHO = False
    # These are set via Render environment variables after frontend is deployed
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'https://your-frontend-domain.onrender.com')
    SOCKETIO_CORS_ORIGINS = os.getenv('SOCKETIO_CORS_ORIGINS', 'https://your-frontend-domain.onrender.com')


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}