# tests/test_inventory.py
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
from routes.inventory import inventory_bp
from models import User, UserRole, UserStatus, Store, ProductCategory, Product, Supplier, InventoryEntry, SupplyRequest, RequestStatus, PaymentStatus

class InventoryTestCase(unittest.TestCase):
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
        self.app.register_blueprint(inventory_bp, url_prefix='/api/inventory')

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

            # Create a product category
            category = ProductCategory(name='Test Category', description='Test Description')
            db.session.add(category)

            # Create a product
            product = Product(
                name='Test Product',
                sku='TEST-PROD-001',
                category_id=1,
                store_id=1,
                min_stock_level=5
            )
            db.session.add(product)

            # Create a supplier
            supplier = Supplier(
                name='Test Supplier',
                contact_person='John Doe',
                phone='123-456-7890',
                email=f'supplier_{self.unique_id}@myduka.com'
            )
            db.session.add(supplier)

            # Create a supply request
            supply_request = SupplyRequest(
                product_id=1,
                quantity_requested=10,
                clerk_id=3,
                status=RequestStatus.PENDING
            )
            db.session.add(supply_request)

            db.session.commit()

            # Generate tokens for testing
            self.admin_token = create_access_token(
                identity={'id': 2, 'role': UserRole.ADMIN.value, 'store_id': 1}
            )
            self.clerk_token = create_access_token(
                identity={'id': 3, 'role': UserRole.CLERK.value, 'store_id': 1}
            )

    def tearDown(self):
        """Tear down test app context"""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_create_product_as_admin(self):
        """Test creating a product as an admin"""
        response = self.client.post('/api/inventory/products', json={
            'name': 'New Product',
            'sku': 'NEW-PROD-001',
            'category_id': 1,
            'store_id': 1,
            'min_stock_level': 5
        }, headers={'Authorization': f'Bearer {self.admin_token}'})
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['product']['name'], 'New Product')

    def test_create_entry_as_clerk(self):
        """Test creating an inventory entry as a clerk"""
        response = self.client.post('/api/inventory/entries', json={
            'product_id': 1,
            'quantity_received': 20,
            'quantity_spoiled': 2,
            'buying_price': 10.0,
            'selling_price': 15.0,
            'supplier_id': 1
        }, headers={'Authorization': f'Bearer {self.clerk_token}'})
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['inventory_entry']['quantity_received'], 20)

        with self.app.app_context():
            product = db.session.get(Product, 1)  # Updated to use Session.get()
            self.assertEqual(product.current_stock, 18)  # 20 - 2 spoiled

    def test_create_supply_request_as_clerk(self):
        """Test creating a supply request as a clerk"""
        response = self.client.post('/api/inventory/supply-requests', json={
            'product_id': 1,
            'quantity_requested': 30
        }, headers={'Authorization': f'Bearer {self.clerk_token}'})
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['supply_request']['quantity_requested'], 30)
        self.assertEqual(data['supply_request']['status'], 'PENDING')

    def test_approve_supply_request_as_admin(self):
        """Test approving a supply request as an admin"""
        response = self.client.put('/api/inventory/supply-requests/1/approve',
                                 headers={'Authorization': f'Bearer {self.admin_token}'})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['supply_request']['status'], 'APPROVED')

    def test_get_products(self):
        """Test retrieving products"""
        response = self.client.get('/api/inventory/products',
                                 headers={'Authorization': f'Bearer {self.admin_token}'})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(len(data['products']), 1)
        self.assertEqual(data['products'][0]['name'], 'Test Product')

    def test_get_inventory_entries(self):
        """Test retrieving inventory entries"""
        # First, create an entry
        self.client.post('/api/inventory/entries', json={
            'product_id': 1,
            'quantity_received': 20,
            'quantity_spoiled': 2,
            'buying_price': 10.0,
            'selling_price': 15.0,
            'supplier_id': 1
        }, headers={'Authorization': f'Bearer {self.clerk_token}'})

        response = self.client.get('/api/inventory/entries',
                                 headers={'Authorization': f'Bearer {self.admin_token}'})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(len(data['entries']), 1)
        self.assertEqual(data['entries'][0]['quantity_received'], 20)

    def test_get_supply_requests(self):
        """Test retrieving supply requests"""
        response = self.client.get('/api/inventory/supply-requests',
                                 headers={'Authorization': f'Bearer {self.clerk_token}'})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(len(data['requests']), 1)
        self.assertEqual(data['requests'][0]['quantity_requested'], 10)

    def test_update_payment_status(self):
        """Test updating payment status of an inventory entry"""
        # First, create an entry
        self.client.post('/api/inventory/entries', json={
            'product_id': 1,
            'quantity_received': 20,
            'quantity_spoiled': 2,
            'buying_price': 10.0,
            'selling_price': 15.0,
            'supplier_id': 1
        }, headers={'Authorization': f'Bearer {self.clerk_token}'})

        response = self.client.put('/api/inventory/update-payment/1', json={
            'payment_status': 'PAID'
        }, headers={'Authorization': f'Bearer {self.admin_token}'})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['message'], 'Payment status updated to paid successfully')

        with self.app.app_context():
            entry = db.session.get(InventoryEntry, 1)  # Updated to use Session.get()
            self.assertEqual(entry.payment_status, PaymentStatus.PAID)

if __name__ == '__main__':
    unittest.main()