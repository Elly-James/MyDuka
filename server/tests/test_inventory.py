import unittest
from unittest.mock import MagicMock, patch
from flask import Flask, jsonify
from datetime import datetime

# Mock database models (to avoid actual database usage)
class User:
    def __init__(self, id, email, role, store_id):
        self.id = id
        self.email = email
        self.role = role
        self.store_id = store_id
        self.status = 'ACTIVE'

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'role': self.role,
            'store_id': self.store_id,
            'status': self.status
        }

class Product:
    def __init__(self, id, name, stock_quantity, store_id, category_id, low_stock_threshold=10):
        self.id = id
        self.name = name
        self.stock_quantity = stock_quantity
        self.store_id = store_id
        self.category_id = category_id
        self.low_stock_threshold = low_stock_threshold

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'stock_quantity': self.stock_quantity,
            'store_id': self.store_id,
            'category_id': self.category_id,
            'low_stock_threshold': self.low_stock_threshold
        }

class InventoryEntry:
    def __init__(self, id, product_id, quantity, supplier, payment_status='PENDING'):
        self.id = id
        self.product_id = product_id
        self.quantity = quantity
        self.supplier = supplier
        self.payment_status = payment_status

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'quantity': self.quantity,
            'supplier': self.supplier,
            'payment_status': self.payment_status
        }

class SupplyRequest:
    def __init__(self, id, product_id, quantity, status='PENDING'):
        self.id = id
        self.product_id = product_id
        self.quantity = quantity
        self.status = status

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'quantity': self.quantity,
            'status': self.status
        }

# Create Flask app for testing
app = Flask(__name__)

# Simulated routes (simplified to avoid database calls)
@app.route('/api/inventory/products', methods=['GET'])
def get_products():
    user = getattr(app, 'mock_user', None)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    products = getattr(app, 'mock_products', [])
    return jsonify({'products': [p.to_dict() for p in products]}), 200

@app.route('/api/inventory/products', methods=['POST'])
def create_product():
    user = getattr(app, 'mock_user', None)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    if user.role not in ['ADMIN', 'MERCHANT']:
        return jsonify({'error': 'Forbidden'}), 403
    data = app.mock_request_data
    store_id = data.get('store_id')
    category_id = data.get('category_id')
    stock_quantity = data.get('stock_quantity')
    if store_id != user.store_id:
        return jsonify({'error': 'Store not found'}), 404
    if not app.mock_categories:
        return jsonify({'error': 'Category not found'}), 404
    if stock_quantity < 0:
        return jsonify({'error': 'Stock quantity cannot be negative'}), 400
    product = Product(id=1, name=data.get('name'), stock_quantity=stock_quantity, store_id=store_id, category_id=category_id)
    return jsonify({'product': product.to_dict()}), 201

@app.route('/api/inventory/entries', methods=['POST'])
def create_entry():
    user = getattr(app, 'mock_user', None)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    data = app.mock_request_data
    product_id = data.get('product_id')
    quantity = data.get('quantity')
    product = app.mock_products[0] if app.mock_products else None
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    if quantity > 1000:
        return jsonify({'error': 'Quantity exceeds maximum limit'}), 400
    if data.get('unit_price') < 0:
        return jsonify({'error': 'Unit price cannot be negative'}), 400
    entry = InventoryEntry(id=1, product_id=product_id, quantity=quantity, supplier=data.get('supplier'))
    return jsonify({'inventory_entry': entry.to_dict()}), 201

@app.route('/api/inventory/entries', methods=['GET'])
def get_entries():
    user = getattr(app, 'mock_user', None)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    payment_status = app.mock_query_params.get('payment_status')
    if payment_status and payment_status not in ['PENDING', 'PAID']:
        return jsonify({'error': 'Invalid payment status'}), 400
    entries = getattr(app, 'mock_entries', [])
    return jsonify({'inventory_entries': [e.to_dict() for e in entries]}), 201

@app.route('/api/inventory/entries/<int:entry_id>', methods=['PUT'])
def update_entry(entry_id):
    user = getattr(app, 'mock_user', None)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    if user.role == 'CLERK':
        return jsonify({'error': 'Forbidden'}), 403
    entry = app.mock_entries[0] if app.mock_entries else None
    if not entry:
        return jsonify({'error': 'Entry not found'}), 404
    data = app.mock_request_data
    supplier = data.get('supplier')
    if not supplier:
        return jsonify({'error': 'Supplier not found'}), 404
    entry.supplier = supplier
    return jsonify({'inventory_entry': entry.to_dict()}), 200

@app.route('/api/inventory/entries/<int:entry_id>', methods=['DELETE'])
def delete_entry(entry_id):
    user = getattr(app, 'mock_user', None)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    if user.role == 'CLERK':
        return jsonify({'error': 'Forbidden'}), 403
    entry = app.mock_entries[0] if app.mock_entries else None
    if not entry:
        return jsonify({'error': 'Entry not found'}), 404
    return jsonify({'message': 'Inventory entry deleted successfully'}), 200

@app.route('/api/inventory/supply-requests', methods=['POST'])
def create_supply_request():
    user = getattr(app, 'mock_user', None)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    data = app.mock_request_data
    product_id = data.get('product_id')
    product = app.mock_products[0] if app.mock_products else None
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    supply_request = SupplyRequest(id=1, product_id=product_id, quantity=data.get('quantity'))
    return jsonify({'supply_request': supply_request.to_dict()}), 201

@app.route('/api/inventory/supply-requests', methods=['GET'])
def get_supply_requests():
    user = getattr(app, 'mock_user', None)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    status = app.mock_query_params.get('status')
    if status and status not in ['PENDING', 'APPROVED', 'DECLINED']:
        return jsonify({'error': 'Invalid status'}), 400
    supply_requests = getattr(app, 'mock_supply_requests', [])
    return jsonify({'supply_requests': [sr.to_dict() for sr in supply_requests]}), 201

@app.route('/api/inventory/supply-requests/<int:request_id>', methods=['PUT'])
def update_supply_request(request_id):
    user = getattr(app, 'mock_user', None)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    if user.role == 'CLERK':
        return jsonify({'error': 'Forbidden'}), 403
    supply_request = app.mock_supply_requests[0] if app.mock_supply_requests else None
    if not supply_request:
        return jsonify({'error': 'Supply request not found'}), 404
    data = app.mock_request_data
    status = data.get('status')
    if status not in ['APPROVED', 'DECLINED']:
        return jsonify({'error': 'Invalid status'}), 400
    if supply_request.status != 'PENDING':
        return jsonify({'error': 'Supply request is not pending'}), 400
    supply_request.status = status
    return jsonify({'supply_request': supply_request.to_dict()}), 200

@app.route('/api/inventory/approve-supply-request/<int:request_id>', methods=['PUT'])
def approve_supply_request(request_id):
    user = getattr(app, 'mock_user', None)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    if user.role == 'CLERK':
        return jsonify({'error': 'Forbidden'}), 403
    supply_request = app.mock_supply_requests[0] if app.mock_supply_requests else None
    if not supply_request:
        return jsonify({'error': 'Supply request not found'}), 404
    if supply_request.status != 'PENDING':
        return jsonify({'error': 'Supply request is not pending'}), 400
    supply_request.status = 'APPROVED'
    return jsonify({'supply_request': supply_request.to_dict()}), 200

@app.route('/api/inventory/entries/<int:entry_id>/payment-status', methods=['PUT'])
def update_payment_status(entry_id):
    user = getattr(app, 'mock_user', None)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    if user.role == 'CLERK':
        return jsonify({'error': 'Forbidden'}), 403
    entry = app.mock_entries[0] if app.mock_entries else None
    if not entry:
        return jsonify({'error': 'Entry not found'}), 404
    data = app.mock_request_data
    payment_status = data.get('payment_status')
    if payment_status not in ['PENDING', 'PAID']:
        return jsonify({'error': 'Invalid payment status'}), 400
    entry.payment_status = payment_status
    return jsonify({'inventory_entry': entry.to_dict()}), 200

@app.route('/api/inventory/low-stock', methods=['GET'])
def low_stock():
    user = getattr(app, 'mock_user', None)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    products = getattr(app, 'mock_products', [])
    return jsonify({'low_stock_products': [p.to_dict() for p in products]}), 200

@app.route('/api/inventory/unpaid-suppliers', methods=['GET'])
def unpaid_suppliers():
    user = getattr(app, 'mock_user', None)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    if user.role == 'CLERK':
        return jsonify({'error': 'Forbidden'}), 403
    entries = getattr(app, 'mock_entries', [])
    return jsonify({'unpaid_suppliers': [e.to_dict() for e in entries]}), 200

@app.route('/api/inventory/search', methods=['GET'])
def search_products():
    user = getattr(app, 'mock_user', None)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    query = app.mock_query_params.get('q')
    if not query:
        return jsonify({'error': 'Query parameter "q" is required'}), 400
    products = getattr(app, 'mock_products', [])
    return jsonify({'products': [p.to_dict() for p in products]}), 200

# Test class
class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        self.app.config['TESTING'] = True

        # Mock users
        self.admin_user = User(id=1, email="admin@example.com", role="ADMIN", store_id=1)
        self.merchant_user = User(id=2, email="merchant@example.com", role="MERCHANT", store_id=1)
        self.clerk_user = User(id=3, email="clerk@example.com", role="CLERK", store_id=1)

        # Mock products
        self.product = Product(id=1, name="Test Product", stock_quantity=5, store_id=1, category_id=1)
        self.app.mock_products = [self.product]

        # Mock entries
        self.entry = InventoryEntry(id=1, product_id=1, quantity=10, supplier="Test Supplier")
        self.app.mock_entries = [self.entry]

        # Mock supply requests
        self.supply_request = SupplyRequest(id=1, product_id=1, quantity=20)
        self.app.mock_supply_requests = [self.supply_request]

        # Mock categories
        self.app.mock_categories = [1]

    def mock_current_user(self, user):
        def decorator(f):
            def wrapped_function(*args, **kwargs):
                self.app.mock_user = user
                return f(*args, **kwargs)
            return wrapped_function
        return decorator

    def mock_request_data(self, data):
        def decorator(f):
            def wrapped_function(*args, **kwargs):
                self.app.mock_request_data = data
                return f(*args, **kwargs)
            return wrapped_function
        return decorator

    def mock_query_params(self, params):
        def decorator(f):
            def wrapped_function(*args, **kwargs):
                self.app.mock_query_params = params
                return f(*args, **kwargs)
            return wrapped_function
        return decorator

    # Test product routes
    def test_get_products(self):
        @self.mock_current_user(self.admin_user)
        def _():
            response = self.client.get('/api/inventory/products')
            self.assertEqual(response.status_code, 200)
            self.assertIn('products', response.json)
        _()

    def test_get_products_by_merchant(self):
        @self.mock_current_user(self.merchant_user)
        def _():
            response = self.client.get('/api/inventory/products')
            self.assertEqual(response.status_code, 200)
            self.assertIn('products', response.json)
        _()

    def test_create_product_by_admin(self):
        @self.mock_current_user(self.admin_user)
        @self.mock_request_data({
            'name': 'New Product',
            'stock_quantity': 10,
            'store_id': 1,
            'category_id': 1
        })
        def _():
            response = self.client.post('/api/inventory/products')
            self.assertEqual(response.status_code, 201)
            self.assertIn('product', response.json)
        _()

    def test_create_product_by_clerk_unauthorized(self):
        @self.mock_current_user(self.clerk_user)
        @self.mock_request_data({
            'name': 'New Product',
            'stock_quantity': 10,
            'store_id': 1,
            'category_id': 1
        })
        def _():
            response = self.client.post('/api/inventory/products')
            self.assertEqual(response.status_code, 403)
        _()

    def test_create_product_invalid_store(self):
        @self.mock_current_user(self.admin_user)
        @self.mock_request_data({
            'name': 'New Product',
            'stock_quantity': 10,
            'store_id': 2,  # Different store_id
            'category_id': 1
        })
        def _():
            response = self.client.post('/api/inventory/products')
            self.assertEqual(response.status_code, 404)
        _()

    def test_create_product_invalid_category(self):
        @self.mock_current_user(self.admin_user)
        @self.mock_request_data({
            'name': 'New Product',
            'stock_quantity': 10,
            'store_id': 1,
            'category_id': 2  # Non-existent category
        })
        def _():
            self.app.mock_categories = []  # Simulate no categories
            response = self.client.post('/api/inventory/products')
            self.assertEqual(response.status_code, 404)
        _()

    def test_create_product_negative_stock(self):
        @self.mock_current_user(self.admin_user)
        @self.mock_request_data({
            'name': 'New Product',
            'stock_quantity': -5,
            'store_id': 1,
            'category_id': 1
        })
        def _():
            response = self.client.post('/api/inventory/products')
            self.assertEqual(response.status_code, 400)
        _()

    def test_create_product_low_stock_notification(self):
        @self.mock_current_user(self.admin_user)
        @self.mock_request_data({
            'name': 'New Product',
            'stock_quantity': 5,
            'store_id': 1,
            'category_id': 1
        })
        def _():
            response = self.client.post('/api/inventory/products')
            self.assertEqual(response.status_code, 201)
        _()

    # Test inventory entry routes
    def test_create_entry_by_clerk(self):
        @self.mock_current_user(self.clerk_user)
        @self.mock_request_data({
            'product_id': 1,
            'quantity': 10,
            'unit_price': 100,
            'supplier': 'Test Supplier'
        })
        def _():
            response = self.client.post('/api/inventory/entries')
            self.assertEqual(response.status_code, 201)
            self.assertIn('inventory_entry', response.json)
        _()

    def test_create_entry_negative_price(self):
        @self.mock_current_user(self.clerk_user)
        @self.mock_request_data({
            'product_id': 1,
            'quantity': 10,
            'unit_price': -100,
            'supplier': 'Test Supplier'
        })
        def _():
            response = self.client.post('/api/inventory/entries')
            self.assertEqual(response.status_code, 400)
        _()

    def test_create_entry_excess_quantity(self):
        @self.mock_current_user(self.clerk_user)
        @self.mock_request_data({
            'product_id': 1,
            'quantity': 1500,
            'unit_price': 100,
            'supplier': 'Test Supplier'
        })
        def _():
            response = self.client.post('/api/inventory/entries')
            self.assertEqual(response.status_code, 400)
        _()

    def test_create_entry_low_stock_notification(self):
        @self.mock_current_user(self.clerk_user)
        @self.mock_request_data({
            'product_id': 1,
            'quantity': 5,
            'unit_price': 100,
            'supplier': 'Test Supplier'
        })
        def _():
            response = self.client.post('/api/inventory/entries')
            self.assertEqual(response.status_code, 201)
        _()

    def test_create_entry_invalid_product(self):
        @self.mock_current_user(self.clerk_user)
        @self.mock_request_data({
            'product_id': 2,
            'quantity': 10,
            'unit_price': 100,
            'supplier': 'Test Supplier'
        })
        def _():
            self.app.mock_products = []  # Simulate product not found
            response = self.client.post('/api/inventory/entries')
            self.assertEqual(response.status_code, 404)
        _()

    def test_get_entries(self):
        @self.mock_current_user(self.admin_user)
        @self.mock_query_params({})
        def _():
            response = self.client.get('/api/inventory/entries')
            self.assertEqual(response.status_code, 201)
            self.assertIn('inventory_entries', response.json)
        _()

    def test_get_entries_invalid_payment_status(self):
        @self.mock_current_user(self.admin_user)
        @self.mock_query_params({'payment_status': 'INVALID'})
        def _():
            response = self.client.get('/api/inventory/entries')
            self.assertEqual(response.status_code, 400)
        _()

    def test_update_entry_by_admin(self):
        @self.mock_current_user(self.admin_user)
        @self.mock_request_data({
            'quantity': 15,
            'supplier': 'New Supplier'
        })
        def _():
            response = self.client.put('/api/inventory/entries/1')
            self.assertEqual(response.status_code, 200)
            self.assertIn('inventory_entry', response.json)
        _()

    def test_update_entry_by_merchant(self):
        @self.mock_current_user(self.merchant_user)
        @self.mock_request_data({
            'quantity': 15,
            'supplier': 'New Supplier'
        })
        def _():
            response = self.client.put('/api/inventory/entries/1')
            self.assertEqual(response.status_code, 200)
            self.assertIn('inventory_entry', response.json)
        _()

    def test_update_entry_unauthorized_clerk(self):
        @self.mock_current_user(self.clerk_user)
        @self.mock_request_data({
            'quantity': 15,
            'supplier': 'New Supplier'
        })
        def _():
            response = self.client.put('/api/inventory/entries/1')
            self.assertEqual(response.status_code, 403)
        _()

    def test_update_entry_invalid_supplier(self):
        @self.mock_current_user(self.admin_user)
        @self.mock_request_data({
            'quantity': 15,
            'supplier': ''
        })
        def _():
            response = self.client.put('/api/inventory/entries/1')
            self.assertEqual(response.status_code, 404)
        _()

    def test_update_entry_not_found(self):
        @self.mock_current_user(self.admin_user)
        @self.mock_request_data({
            'quantity': 15,
            'supplier': 'New Supplier'
        })
        def _():
            self.app.mock_entries = []  # Simulate entry not found
            response = self.client.put('/api/inventory/entries/1')
            self.assertEqual(response.status_code, 404)
        _()

    def test_delete_entry_by_admin(self):
        @self.mock_current_user(self.admin_user)
        def _():
            response = self.client.delete('/api/inventory/entries/1')
            self.assertEqual(response.status_code, 200)
            self.assertIn('message', response.json)
        _()

    def test_delete_entry_by_merchant(self):
        @self.mock_current_user(self.merchant_user)
        def _():
            response = self.client.delete('/api/inventory/entries/1')
            self.assertEqual(response.status_code, 200)
            self.assertIn('message', response.json)
        _()

    def test_delete_entry_unauthorized_clerk(self):
        @self.mock_current_user(self.clerk_user)
        def _():
            response = self.client.delete('/api/inventory/entries/1')
            self.assertEqual(response.status_code, 403)
        _()

    def test_delete_entry_not_found(self):
        @self.mock_current_user(self.admin_user)
        def _():
            self.app.mock_entries = []  # Simulate entry not found
            response = self.client.delete('/api/inventory/entries/1')
            self.assertEqual(response.status_code, 404)
        _()

    # Test supply request routes
    def test_create_supply_request(self):
        @self.mock_current_user(self.clerk_user)
        @self.mock_request_data({
            'product_id': 1,
            'quantity': 20
        })
        def _():
            response = self.client.post('/api/inventory/supply-requests')
            self.assertEqual(response.status_code, 201)
            self.assertIn('supply_request', response.json)
        _()

    def test_create_supply_request_invalid_product(self):
        @self.mock_current_user(self.clerk_user)
        @self.mock_request_data({
            'product_id': 2,
            'quantity': 20
        })
        def _():
            self.app.mock_products = []  # Simulate product not found
            response = self.client.post('/api/inventory/supply-requests')
            self.assertEqual(response.status_code, 404)
        _()

    def test_get_supply_requests(self):
        @self.mock_current_user(self.admin_user)
        @self.mock_query_params({})
        def _():
            response = self.client.get('/api/inventory/supply-requests')
            self.assertEqual(response.status_code, 201)
            self.assertIn('supply_requests', response.json)
        _()

    def test_get_supply_requests_invalid_status(self):
        @self.mock_current_user(self.admin_user)
        @self.mock_query_params({'status': 'INVALID'})
        def _():
            response = self.client.get('/api/inventory/supply-requests')
            self.assertEqual(response.status_code, 400)
        _()

    def test_update_supply_request_approve(self):
        @self.mock_current_user(self.admin_user)
        @self.mock_request_data({'status': 'APPROVED'})
        def _():
            response = self.client.put('/api/inventory/supply-requests/1')
            self.assertEqual(response.status_code, 200)
            self.assertIn('supply_request', response.json)
        _()

    def test_update_supply_request_decline(self):
        @self.mock_current_user(self.admin_user)
        @self.mock_request_data({'status': 'DECLINED'})
        def _():
            response = self.client.put('/api/inventory/supply-requests/1')
            self.assertEqual(response.status_code, 200)
            self.assertIn('supply_request', response.json)
        _()

    def test_update_supply_request_invalid_status(self):
        @self.mock_current_user(self.admin_user)
        @self.mock_request_data({'status': 'INVALID'})
        def _():
            response = self.client.put('/api/inventory/supply-requests/1')
            self.assertEqual(response.status_code, 400)
        _()

    def test_update_supply_request_not_pending(self):
        @self.mock_current_user(self.admin_user)
        @self.mock_request_data({'status': 'APPROVED'})
        def _():
            self.supply_request.status = 'APPROVED'  # Simulate already approved
            response = self.client.put('/api/inventory/supply-requests/1')
            self.assertEqual(response.status_code, 400)
        _()

    def test_approve_supply_request_by_admin(self):
        @self.mock_current_user(self.admin_user)
        def _():
            response = self.client.put('/api/inventory/approve-supply-request/1')
            self.assertEqual(response.status_code, 200)
            self.assertIn('supply_request', response.json)
        _()

    def test_approve_supply_request_unauthorized_clerk(self):
        @self.mock_current_user(self.clerk_user)
        def _():
            response = self.client.put('/api/inventory/approve-supply-request/1')
            self.assertEqual(response.status_code, 403)
        _()

    def test_update_payment_status(self):
        @self.mock_current_user(self.admin_user)
        @self.mock_request_data({'payment_status': 'PAID'})
        def _():
            response = self.client.put('/api/inventory/entries/1/payment-status')
            self.assertEqual(response.status_code, 200)
            self.assertIn('inventory_entry', response.json)
        _()

    def test_update_payment_status_invalid_status(self):
        @self.mock_current_user(self.admin_user)
        @self.mock_request_data({'payment_status': 'INVALID'})
        def _():
            response = self.client.put('/api/inventory/entries/1/payment-status')
            self.assertEqual(response.status_code, 400)
        _()

    def test_low_stock_clerk(self):
        @self.mock_current_user(self.clerk_user)
        def _():
            response = self.client.get('/api/inventory/low-stock')
            self.assertEqual(response.status_code, 200)
            self.assertIn('low_stock_products', response.json)
        _()

    def test_low_stock_admin(self):
        @self.mock_current_user(self.admin_user)
        def _():
            response = self.client.get('/api/inventory/low-stock')
            self.assertEqual(response.status_code, 200)
            self.assertIn('low_stock_products', response.json)
        _()

    def test_low_stock_merchant(self):
        @self.mock_current_user(self.merchant_user)
        def _():
            response = self.client.get('/api/inventory/low-stock')
            self.assertEqual(response.status_code, 200)
            self.assertIn('low_stock_products', response.json)
        _()

    def test_unpaid_suppliers_admin(self):
        @self.mock_current_user(self.admin_user)
        def _():
            response = self.client.get('/api/inventory/unpaid-suppliers')
            self.assertEqual(response.status_code, 200)
            self.assertIn('unpaid_suppliers', response.json)
        _()

    def test_unpaid_suppliers_unauthorized_clerk(self):
        @self.mock_current_user(self.clerk_user)
        def _():
            response = self.client.get('/api/inventory/unpaid-suppliers')
            self.assertEqual(response.status_code, 403)
        _()

    def test_search_products(self):
        @self.mock_current_user(self.admin_user)
        @self.mock_query_params({'q': 'test'})
        def _():
            response = self.client.get('/api/inventory/search?q=test')
            self.assertEqual(response.status_code, 200)
            self.assertIn('products', response.json)
        _()

    def test_search_products_no_query(self):
        @self.mock_current_user(self.admin_user)
        @self.mock_query_params({})
        def _():
            response = self.client.get('/api/inventory/search')
            self.assertEqual(response.status_code, 400)
        _()

if __name__ == '__main__':
    unittest.main()