# tests/test_auth.py
import os
import sys
import time
from datetime import datetime, timedelta
import unittest
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token

# Add the parent directory (server) to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables before importing config
from dotenv import load_dotenv
load_dotenv()

from config import config
from extensions import db, mail
from routes.auth import auth_bp
from models import User, UserRole, UserStatus, Invitation, Store

class AuthTestCase(unittest.TestCase):
    def setUp(self):
        """Set up test app and client"""
        self.app = Flask(__name__)
        self.app.config.from_object(config['testing'])
        self.app.config['INVITATION_EXPIRY'] = timedelta(days=1)
        # Set JWT_SECRET_KEY (required by JWTManager)
        self.app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'your-jwt-secret-key')
        # Initialize extensions
        db.init_app(self.app)
        jwt = JWTManager(self.app)
        mail.init_app(self.app)
        # Register blueprints
        self.app.register_blueprint(auth_bp, url_prefix='/api/auth')

        self.client = self.app.test_client()

        # Use a unique identifier for emails to avoid conflicts
        self.unique_id = str(int(time.time() * 1000))

        with self.app.app_context():
            # Drop and recreate all tables to ensure a clean state
            db.drop_all()
            db.create_all()

            # Create a merchant user
            merchant = User(
                name='Test Merchant',
                email=f'merchant_{self.unique_id}@myduka.com',
                role=UserRole.MERCHANT,
                status=UserStatus.ACTIVE
            )
            merchant.password = 'password123'
            db.session.add(merchant)

            # Create a store
            store = Store(name='Test Store', location='123 Test St')
            db.session.add(store)

            # Create an invitation for testing
            invitation = Invitation(
                email=f'admin_{self.unique_id}@myduka.com',
                token='test-token',
                role=UserRole.ADMIN,
                creator_id=1,
                store_id=1,
                expires_at=datetime.utcnow() + timedelta(days=1)
            )
            db.session.add(invitation)
            db.session.commit()

            # Generate token for merchant
            self.merchant_token = create_access_token(
                identity={'id': 1, 'role': UserRole.MERCHANT.value, 'store_id': None}
            )

    def tearDown(self):
        """Tear down test app context"""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_login_merchant(self):
        """Test merchant login"""
        response = self.client.post('/api/auth/login', json={
            'email': f'merchant_{self.unique_id}@myduka.com',
            'password': 'password123'
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('access_token', data)

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = self.client.post('/api/auth/login', json={
            'email': f'merchant_{self.unique_id}@myduka.com',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertEqual(data['status'], 'error')
        self.assertEqual(data['message'], 'Invalid email or password')

    def test_register_with_invitation(self):
        """Test registration with a valid invitation"""
        response = self.client.post('/api/auth/register', json={
            'token': 'test-token',
            'email': f'admin_{self.unique_id}@myduka.com',
            'name': 'Test Admin',
            'password': 'admin123'
        })
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['message'], 'Registration successful')

        with self.app.app_context():
            user = User.query.filter_by(email=f'admin_{self.unique_id}@myduka.com').first()
            self.assertIsNotNone(user)
            self.assertEqual(user.name, 'Test Admin')
            self.assertEqual(user.role, UserRole.ADMIN)

    def test_invite_user_as_merchant(self):
        """Test inviting an admin as a merchant"""
        response = self.client.post('/api/auth/invite', json={
            'email': f'newadmin_{self.unique_id}@myduka.com',
            'role': 'ADMIN',
            'store_id': 1
        }, headers={'Authorization': f'Bearer {self.merchant_token}'})
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['message'], 'Invitation sent successfully')

        with self.app.app_context():
            invitation = Invitation.query.filter_by(email=f'newadmin_{self.unique_id}@myduka.com').first()
            self.assertIsNotNone(invitation)
            self.assertFalse(invitation.is_used)

    def test_get_current_user(self):
        """Test retrieving current user information"""
        response = self.client.get('/api/auth/me',
                                 headers={'Authorization': f'Bearer {self.merchant_token}'})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['user']['email'], f'merchant_{self.unique_id}@myduka.com')
        self.assertEqual(data['user']['role'], 'MERCHANT')

if __name__ == '__main__':
    unittest.main()