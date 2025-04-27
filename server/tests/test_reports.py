# tests/test_reports.py
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
from routes.reports import reports_bp
from models import User, UserRole, UserStatus, Store, ProductCategory, Product, Supplier, InventoryEntry, PaymentStatus

class ReportsTestCase(unittest.TestCase):
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
        self.app.register_blueprint(reports_bp, url_prefix='/api/reports')

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

            # Create an inventory entry
            entry = InventoryEntry(
                product_id=1,
                quantity_received=20,
                quantity_spoiled=2,
                buying_price=10.0,
                selling_price=15.0,
                payment_status=PaymentStatus.PAID,
                supplier_id=1,
                recorded_by=2,
                entry_date=datetime.utcnow()
            )
            db.session.add(entry)

            db.session.commit()

            # Update product stock
            product = db.session.get(Product, 1)  # Updated to use Session.get()
            product.current_stock = 18  # 20 - 2 spoiled
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

    def test_sales_report_as_merchant(self):
        """Test sales report generation as a merchant"""
        response = self.client.get('/api/reports/sales',
                                 headers={'Authorization': f'Bearer {self.merchant_token}'})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('total_revenue', data['report'])
        self.assertIn('total_quantity_sold', data['report'])
        self.assertEqual(data['report']['total_quantity_sold'], 20)
        self.assertEqual(data['report']['total_revenue'], 300.0)  # 20 * 15.0

    def test_payment_status_report_as_merchant(self):
        """Test payment status report as a merchant"""
        response = self.client.get('/api/reports/payment-status',
                                 headers={'Authorization': f'Bearer {self.merchant_token}'})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('total_paid', data['report'])
        self.assertIn('total_unpaid', data['report'])
        self.assertEqual(data['report']['total_paid'], 200.0)  # 20 * 10.0
        self.assertEqual(data['report']['total_unpaid'], 0.0)

    def test_spoilage_report_as_admin(self):
        """Test spoilage report as an admin"""
        response = self.client.get('/api/reports/spoilage',
                                 headers={'Authorization': f'Bearer {self.admin_token}'})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('total_spoilage', data['report'])
        self.assertEqual(data['report']['total_spoilage'], 2)  # 2 spoiled units

if __name__ == '__main__':
    unittest.main()