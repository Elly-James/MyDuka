# tests/test_users.py
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
from extensions import db
from routes.users import users_bp
from models import User, UserRole, UserStatus, Store

class UsersTestCase(unittest.TestCase):
    def setUp(self):
        """Set up test app and client"""
        self.app = Flask(__name__)
        self.app.config.from_object(config['testing'])
        # Set JWT_SECRET_KEY (required by JWTManager)
        self.app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'your-jwt-secret-key')
        # Initialize extensions
        db.init_app(self.app)
        jwt = JWTManager(self.app)
        # Register blueprints
        self.app.register_blueprint(users_bp, url_prefix='/api/users')

        self.client = self.app.test_client()

        # Use a unique identifier for emails to avoid conflicts
        self.unique_id = str(int(time.time() * 1000))

        with self.app.app_context():
            # Drop and recreate all tables to ensure a clean state
            db.drop_all()
            db.create_all()

            # Create a merchant
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

            # Create an admin
            admin = User(
                name='Test Admin',
                email=f'admin_{self.unique_id}@myduka.com',
                role=UserRole.ADMIN,
                status=UserStatus.ACTIVE,
                store_id=1
            )
            admin.password = 'admin123'
            db.session.add(admin)

            # Create a clerk
            clerk = User(
                name='Test Clerk',
                email=f'clerk_{self.unique_id}@myduka.com',
                role=UserRole.CLERK,
                status=UserStatus.ACTIVE,
                store_id=1
            )
            clerk.password = 'clerk123'
            db.session.add(clerk)

            db.session.commit()

            # Generate tokens for testing
            self.merchant_token = create_access_token(
                identity={'id': 1, 'role': UserRole.MERCHANT.value, 'store_id': None}
            )
            self.admin_token = create_access_token(
                identity={'id': 2, 'role': UserRole.ADMIN.value, 'store_id': 1}
            )

    def tearDown(self):
        """Tear down test app context"""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_get_users_as_merchant(self):
        """Test retrieving users as a merchant"""
        response = self.client.get('/api/users',
                                 headers={'Authorization': f'Bearer {self.merchant_token}'},
                                 follow_redirects=True)  # Added follow_redirects=True
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(len(data['users']), 3)  # Merchant, admin, clerk
        self.assertEqual(data['users'][0]['email'], f'merchant_{self.unique_id}@myduka.com')

    def test_get_users_as_admin(self):
        """Test retrieving users as an admin"""
        response = self.client.get('/api/users',
                                 headers={'Authorization': f'Bearer {self.admin_token}'},
                                 follow_redirects=True)  # Added follow_redirects=True
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(len(data['users']), 2)  # Admin and clerk (same store)
        self.assertEqual(data['users'][0]['email'], f'admin_{self.unique_id}@myduka.com')

    def test_update_user_status_as_merchant(self):
        """Test updating user status as a merchant"""
        response = self.client.put('/api/users/2/status', json={
            'status': 'INACTIVE'
        }, headers={'Authorization': f'Bearer {self.merchant_token}'})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['message'], 'User status updated to inactive successfully')

        with self.app.app_context():
            user = db.session.get(User, 2)  # Updated to use Session.get()
            self.assertEqual(user.status, UserStatus.INACTIVE)

    def test_delete_user_as_admin(self):
        """Test deleting a user as an admin"""
        response = self.client.delete('/api/users/3',
                                    headers={'Authorization': f'Bearer {self.admin_token}'})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['message'], 'User deleted successfully')

        with self.app.app_context():
            user = db.session.get(User, 3)  # Updated to use Session.get()
            self.assertIsNone(user)

if __name__ == '__main__':
    unittest.main()