import unittest
from flask import Flask, jsonify, Response
from datetime import datetime, timedelta

# Mock enums
class UserRole:
    ADMIN = 'ADMIN'
    MERCHANT = 'MERCHANT'
    CLERK = 'CLERK'

class UserStatus:
    ACTIVE = 'ACTIVE'

class PaymentStatus:
    PAID = 'PAID'
    UNPAID = 'UNPAID'

# Mock models (to avoid actual database usage)
class User:
    def __init__(self, id, email, name, role, status, store_id=None):
        self.id = id
        self.email = email
        self.name = name
        self.role = role
        self.status = status
        self.store_id = store_id

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'role': self.role,
            'status': self.status,
            'store_id': self.store_id
        }

class Store:
    def __init__(self, id, name, location):
        self.id = id
        self.name = name
        self.location = location

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'location': self.location
        }

class ProductCategory:
    def __init__(self, id, name):
        self.id = id
        self.name = name

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name
        }

class Product:
    def __init__(self, id, name, sku, category_id, store_id, current_stock, min_stock_level):
        self.id = id
        self.name = name
        self.sku = sku
        self.category_id = category_id
        self.store_id = store_id
        self.current_stock = current_stock
        self.min_stock_level = min_stock_level

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'sku': self.sku,
            'category_id': self.category_id,
            'store_id': self.store_id,
            'current_stock': self.current_stock,
            'min_stock_level': self.min_stock_level
        }

class InventoryEntry:
    def __init__(self, id, product_id, quantity_received, quantity_spoiled, buying_price, selling_price, payment_status, recorded_by, entry_date):
        self.id = id
        self.product_id = product_id
        self.quantity_received = quantity_received
        self.quantity_spoiled = quantity_spoiled
        self.buying_price = buying_price
        self.selling_price = selling_price
        self.payment_status = payment_status
        self.recorded_by = recorded_by
        self.entry_date = entry_date

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'quantity_received': self.quantity_received,
            'quantity_spoiled': self.quantity_spoiled,
            'buying_price': self.buying_price,
            'selling_price': self.selling_price,
            'payment_status': self.payment_status,
            'recorded_by': self.recorded_by,
            'entry_date': self.entry_date.isoformat()
        }

# Create Flask app for testing
app = Flask(__name__)

# Simulated routes (simplified to avoid database calls)
@app.route('/api/reports/sales', methods=['GET'])
def sales_report():
    user = getattr(app, 'mock_user', None)
    if not user:
        return jsonify({'msg': 'Missing Authorization Header'}), 401

    query_params = getattr(app, 'mock_query_params', {})
    period = query_params.get('period', 'weekly')
    start_date_str = query_params.get('start_date')
    end_date_str = query_params.get('end_date')

    # Validate period
    if period not in ['weekly', 'monthly', 'annual']:
        return jsonify({'status': 'error', 'message': 'Invalid period. Use weekly, monthly, or annual'}), 400

    # Parse dates
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else None
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else None
        if start_date and end_date and start_date > end_date:
            return jsonify({'status': 'error', 'message': 'Start date must be before end date'}), 400
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Invalid date format. Use YYYY-MM-DD'}), 400

    entries = getattr(app, 'mock_inventory_entries', [])
    stores = getattr(app, 'mock_stores', [])
    # Filter entries by store_id for non-merchants
    if user.role != UserRole.MERCHANT:
        entries = [e for e in entries if any(s.id == user.store_id for s in stores if s.id == e.product.store_id)]

    # Filter by date range if provided
    if start_date and end_date:
        entries = [e for e in entries if start_date <= e.entry_date <= end_date]

    total_quantity_sold = sum(e.quantity_received for e in entries)
    total_revenue = sum(e.quantity_received * e.selling_price for e in entries)

    # Mock chart data
    chart_data = {
        'labels': ['Week 1'] if period == 'weekly' else ['Month 1'] if period == 'monthly' else ['Year 1'],
        'datasets': [
            {'label': 'Revenue', 'data': [total_revenue]},
            {'label': 'Quantity Sold', 'data': [total_quantity_sold]}
        ]
    }

    return jsonify({
        'status': 'success',
        'report': {
            'total_quantity_sold': total_quantity_sold,
            'total_revenue': total_revenue,
            'chart_data': chart_data
        }
    }), 200

@app.route('/api/reports/spoilage', methods=['GET'])
def spoilage_report():
    user = getattr(app, 'mock_user', None)
    if not user:
        return jsonify({'msg': 'Missing Authorization Header'}), 401

    query_params = getattr(app, 'mock_query_params', {})
    start_date_str = query_params.get('start_date')
    end_date_str = query_params.get('end_date')

    # Parse dates
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else None
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else None
        if start_date and end_date and start_date > end_date:
            return jsonify({'status': 'error', 'message': 'Start date must be before end date'}), 400
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Invalid date format. Use YYYY-MM-DD'}), 400

    entries = getattr(app, 'mock_inventory_entries', [])
    categories = getattr(app, 'mock_categories', [])
    stores = getattr(app, 'mock_stores', [])
    # Filter entries by store_id for non-merchants
    if user.role != UserRole.MERCHANT:
        entries = [e for e in entries if any(s.id == user.store_id for s in stores if s.id == e.product.store_id)]

    # Filter by date range if provided
    if start_date and end_date:
        entries = [e for e in entries if start_date <= e.entry_date <= end_date]

    total_spoilage = sum(e.quantity_spoiled for e in entries)
    # Mock chart data
    chart_data = {
        'labels': [c.name for c in categories],
        'datasets': [
            {'label': 'Spoilage', 'data': [sum(e.quantity_spoiled for e in entries if e.product.category_id == c.id) for c in categories]}
        ]
    }

    return jsonify({
        'status': 'success',
        'report': {
            'total_spoilage': total_spoilage,
            'chart_data': chart_data
        }
    }), 200

@app.route('/api/reports/payment-status', methods=['GET'])
def payment_status_report():
    user = getattr(app, 'mock_user', None)
    if not user:
        return jsonify({'msg': 'Missing Authorization Header'}), 401

    query_params = getattr(app, 'mock_query_params', {})
    start_date_str = query_params.get('start_date')
    end_date_str = query_params.get('end_date')

    # Parse dates
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else None
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else None
        if start_date and end_date and start_date > end_date:
            return jsonify({'status': 'error', 'message': 'Start date must be before end date'}), 400
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Invalid date format. Use YYYY-MM-DD'}), 400

    entries = getattr(app, 'mock_inventory_entries', [])
    stores = getattr(app, 'mock_stores', [])
    # Filter entries by store_id for non-merchants
    if user.role != UserRole.MERCHANT:
        entries = [e for e in entries if any(s.id == user.store_id for s in stores if s.id == e.product.store_id)]

    # Filter by date range if provided
    if start_date and end_date:
        entries = [e for e in entries if start_date <= e.entry_date <= end_date]

    total_paid = sum(e.quantity_received * e.buying_price for e in entries if e.payment_status == PaymentStatus.PAID)
    total_unpaid = sum(e.quantity_received * e.buying_price for e in entries if e.payment_status == PaymentStatus.UNPAID)

    chart_data = {
        'labels': ['Paid', 'Unpaid'],
        'datasets': [
            {'label': 'Amount', 'data': [total_paid, total_unpaid]}
        ]
    }

    return jsonify({
        'status': 'success',
        'report': {
            'total_paid': total_paid,
            'total_unpaid': total_unpaid,
            'chart_data': chart_data
        }
    }), 200

@app.route('/api/reports/store-comparison', methods=['GET'])
def store_comparison():
    user = getattr(app, 'mock_user', None)
    if not user:
        return jsonify({'msg': 'Missing Authorization Header'}), 401
    if user.role != UserRole.MERCHANT:
        return jsonify({'status': 'error', 'message': 'Unauthorized to view store comparison'}), 403

    query_params = getattr(app, 'mock_query_params', {})
    start_date_str = query_params.get('start_date')
    end_date_str = query_params.get('end_date')

    # Parse dates
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else None
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else None
        if start_date and end_date and start_date > end_date:
            return jsonify({'status': 'error', 'message': 'Start date must be before end date'}), 400
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Invalid date format. Use YYYY-MM-DD'}), 400

    entries = getattr(app, 'mock_inventory_entries', [])
    stores = getattr(app, 'mock_stores', [])

    # Filter by date range if provided
    if start_date and end_date:
        entries = [e for e in entries if start_date <= e.entry_date <= end_date]

    # Group by store
    store_revenue = {}
    store_spoilage = {}
    for store in stores:
        store_entries = [e for e in entries if e.product.store_id == store.id]
        store_revenue[store.name] = sum(e.quantity_received * e.selling_price for e in store_entries)
        store_spoilage[store.name] = sum(e.quantity_spoiled for e in store_entries)

    chart_data = {
        'labels': [store.name for store in stores if store_revenue[store.name] > 0 or store_spoilage[store.name] > 0],
        'datasets': [
            {'label': 'Revenue', 'data': [store_revenue[store.name] for store in stores if store_revenue[store.name] > 0 or store_spoilage[store.name] > 0]},
            {'label': 'Spoilage', 'data': [store_spoilage[store.name] for store in stores if store_revenue[store.name] > 0 or store_spoilage[store.name] > 0]}
        ]
    }

    return jsonify({
        'status': 'success',
        'report': {
            'chart_data': chart_data
        }
    }), 200

@app.route('/api/reports/sales/chart-data', methods=['GET'])
def sales_chart_data():
    user = getattr(app, 'mock_user', None)
    if not user:
        return jsonify({'msg': 'Missing Authorization Header'}), 401

    query_params = getattr(app, 'mock_query_params', {})
    start_date_str = query_params.get('start_date')
    end_date_str = query_params.get('end_date')

    # Parse dates
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else None
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else None
        if start_date and end_date and start_date > end_date:
            return jsonify({'status': 'error', 'message': 'Start date must be before end date'}), 400
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Invalid date format. Use YYYY-MM-DD'}), 400

    entries = getattr(app, 'mock_inventory_entries', [])
    stores = getattr(app, 'mock_stores', [])
    # Filter entries by store_id for non-merchants
    if user.role != UserRole.MERCHANT:
        entries = [e for e in entries if any(s.id == user.store_id for s in stores if s.id == e.product.store_id)]

    # Filter by date range if provided
    if start_date and end_date:
        entries = [e for e in entries if start_date <= e.entry_date <= end_date]

    total_revenue = sum(e.quantity_received * e.selling_price for e in entries)
    total_spoilage = sum(e.quantity_spoiled for e in entries)

    chart_data = {
        'weekly': {
            'labels': ['Week 1'],
            'datasets': [
                {'label': 'Revenue', 'data': [total_revenue]},
                {'label': 'Spoilage', 'data': [total_spoilage]}
            ]
        },
        'monthly': {
            'labels': ['Month 1'],
            'datasets': [
                {'label': 'Revenue', 'data': [total_revenue]},
                {'label': 'Spoilage', 'data': [total_spoilage]}
            ]
        },
        'annual': {
            'labels': ['Year 1'],
            'datasets': [
                {'label': 'Revenue', 'data': [total_revenue]},
                {'label': 'Spoilage', 'data': [total_spoilage]}
            ]
        }
    }

    return jsonify({
        'status': 'success',
        'chart_data': chart_data
    }), 200

@app.route('/api/reports/clerk-performance', methods=['GET'])
def clerk_performance():
    user = getattr(app, 'mock_user', None)
    if not user:
        return jsonify({'msg': 'Missing Authorization Header'}), 401
    if user.role == UserRole.CLERK:
        return jsonify({'status': 'error', 'message': 'Unauthorized to view clerk performance'}), 403

    query_params = getattr(app, 'mock_query_params', {})
    clerk_id = query_params.get('clerk_id')
    if not clerk_id:
        return jsonify({'status': 'error', 'message': 'Clerk ID is required'}), 400

    clerk_id = int(clerk_id)
    users = getattr(app, 'mock_users', [])
    clerk = next((u for u in users if u.id == clerk_id and u.role == UserRole.CLERK), None)
    if not clerk:
        return jsonify({'status': 'error', 'message': 'Clerk not found'}), 404

    start_date_str = query_params.get('start_date')
    end_date_str = query_params.get('end_date')

    # Parse dates
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else None
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else None
        if start_date and end_date and start_date > end_date:
            return jsonify({'status': 'error', 'message': 'Start date must be before end date'}), 400
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Invalid date format. Use YYYY-MM-DD'}), 400

    entries = getattr(app, 'mock_inventory_entries', [])
    stores = getattr(app, 'mock_stores', [])
    # Filter entries by store_id for non-merchants
    if user.role != UserRole.MERCHANT:
        entries = [e for e in entries if any(s.id == user.store_id for s in stores if s.id == e.product.store_id)]

    # Filter by clerk and date range
    entries = [e for e in entries if e.recorded_by == clerk_id]
    if start_date and end_date:
        entries = [e for e in entries if start_date <= e.entry_date <= end_date]

    total_entries = len(entries)
    total_spoiled = sum(e.quantity_spoiled for e in entries)
    total_sales = sum(e.quantity_received * e.selling_price for e in entries)

    return jsonify({
        'status': 'success',
        'report': {
            'total_entries': total_entries,
            'total_spoiled': total_spoiled,
            'total_sales': total_sales
        }
    }), 200

@app.route('/api/reports/export', methods=['GET'])
def export_report():
    user = getattr(app, 'mock_user', None)
    if not user:
        return jsonify({'msg': 'Missing Authorization Header'}), 401

    query_params = getattr(app, 'mock_query_params', {})
    report_type = query_params.get('type')
    report_format = query_params.get('format')

    if report_type not in ['sales', 'spoilage', 'payment-status']:
        return jsonify({'status': 'error', 'message': 'Invalid report type. Use sales, spoilage, or payment-status'}), 400
    if report_format not in ['pdf', 'excel']:
        return jsonify({'status': 'error', 'message': 'Invalid format. Use pdf or excel'}), 400

    if report_format == 'pdf':
        content_type = 'application/pdf'
        filename = f'{report_type}_report.pdf'
    else:  # excel
        content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        filename = f'{report_type}_report.xlsx'

    # Simulate file response without generating actual file
    response = Response(b"Mock file content", mimetype=content_type)
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response

@app.route('/api/reports/chart-data/sales-trend', methods=['GET'])
def sales_trend_chart():
    user = getattr(app, 'mock_user', None)
    if not user:
        return jsonify({'msg': 'Missing Authorization Header'}), 401

    query_params = getattr(app, 'mock_query_params', {})
    period = query_params.get('period', 'monthly')
    start_date_str = query_params.get('start_date')
    end_date_str = query_params.get('end_date')

    # Validate period
    if period not in ['weekly', 'monthly', 'annual']:
        return jsonify({'status': 'error', 'message': 'Invalid period. Use weekly, monthly, or annual'}), 400

    # Parse dates
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else None
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else None
        if start_date and end_date and start_date > end_date:
            return jsonify({'status': 'error', 'message': 'Start date must be before end date'}), 400
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Invalid date format. Use YYYY-MM-DD'}), 400

    entries = getattr(app, 'mock_inventory_entries', [])
    stores = getattr(app, 'mock_stores', [])
    # Filter entries by store_id for non-merchants
    if user.role != UserRole.MERCHANT:
        entries = [e for e in entries if any(s.id == user.store_id for s in stores if s.id == e.product.store_id)]

    # Filter by date range if provided
    if start_date and end_date:
        entries = [e for e in entries if start_date <= e.entry_date <= end_date]

    total_revenue = sum(e.quantity_received * e.selling_price for e in entries)

    chart_data = {
        'labels': ['Period 1'],
        'datasets': [
            {'label': 'Revenue', 'data': [total_revenue]}
        ]
    }

    return jsonify({
        'status': 'success',
        'chart_data': chart_data
    }), 200

@app.route('/api/reports/chart-data/spoilage-by-category', methods=['GET'])
def spoilage_by_category():
    user = getattr(app, 'mock_user', None)
    if not user:
        return jsonify({'msg': 'Missing Authorization Header'}), 401

    query_params = getattr(app, 'mock_query_params', {})
    start_date_str = query_params.get('start_date')
    end_date_str = query_params.get('end_date')

    # Parse dates
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else None
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else None
        if start_date and end_date and start_date > end_date:
            return jsonify({'status': 'error', 'message': 'Start date must be before end date'}), 400
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Invalid date format. Use YYYY-MM-DD'}), 400

    entries = getattr(app, 'mock_inventory_entries', [])
    categories = getattr(app, 'mock_categories', [])
    stores = getattr(app, 'mock_stores', [])
    # Filter entries by store_id for non-merchants
    if user.role != UserRole.MERCHANT:
        entries = [e for e in entries if any(s.id == user.store_id for s in stores if s.id == e.product.store_id)]

    # Filter by date range if provided
    if start_date and end_date:
        entries = [e for e in entries if start_date <= e.entry_date <= end_date]

    chart_data = {
        'labels': [c.name for c in categories],
        'datasets': [
            {'label': 'Spoilage', 'data': [sum(e.quantity_spoiled for e in entries if e.product.category_id == c.id) for c in categories]}
        ]
    }

    return jsonify({
        'status': 'success',
        'chart_data': chart_data
    }), 200

# Test class
class ReportsTests(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        self.app.config['TESTING'] = True

        # Mock users
        self.merchant_user = User(id=1, email="merchant@test.com", name="Test Merchant", role=UserRole.MERCHANT, status=UserStatus.ACTIVE)
        self.admin_user = User(id=2, email="admin@test.com", name="Test Admin", role=UserRole.ADMIN, status=UserStatus.ACTIVE, store_id=1)
        self.clerk_user = User(id=3, email="clerk@test.com", name="Test Clerk", role=UserRole.CLERK, status=UserStatus.ACTIVE, store_id=1)

        # Mock stores
        self.store1 = Store(id=1, name="Store 1", location="123 Test St")
        self.store2 = Store(id=2, name="Store 2", location="456 Test St")
        self.app.mock_stores = [self.store1, self.store2]

        # Mock categories
        self.category = ProductCategory(id=1, name="Test Category")
        self.app.mock_categories = [self.category]

        # Mock products
        self.product1 = Product(id=1, name="Product 1", sku="P1", category_id=self.category.id, store_id=self.store1.id, current_stock=10, min_stock_level=5)
        self.product2 = Product(id=2, name="Product 2", sku="P2", category_id=self.category.id, store_id=self.store2.id, current_stock=20, min_stock_level=10)

        # Mock inventory entries
        self.entry1 = InventoryEntry(
            id=1,
            product_id=self.product1.id,
            quantity_received=20,
            quantity_spoiled=2,
            buying_price=10.0,
            selling_price=15.0,
            payment_status=PaymentStatus.UNPAID,
            recorded_by=self.clerk_user.id,
            entry_date=datetime.utcnow() - timedelta(days=10)
        )
        self.entry2 = InventoryEntry(
            id=2,
            product_id=self.product2.id,
            quantity_received=30,
            quantity_spoiled=3,
            buying_price=12.0,
            selling_price=18.0,
            payment_status=PaymentStatus.PAID,
            recorded_by=self.clerk_user.id,
            entry_date=datetime.utcnow() - timedelta(days=1)  # Adjusted to be 1 day ago
        )
        self.app.mock_inventory_entries = [self.entry1, self.entry2]

        # Attach products to entries for easier lookup
        self.entry1.product = self.product1
        self.entry2.product = self.product2

        # Mock users list for clerk lookup
        self.app.mock_users = [self.merchant_user, self.admin_user, self.clerk_user]

    def tearDown(self):
        # Clear mock_user to prevent state leakage between tests
        if hasattr(self.app, 'mock_user'):
            delattr(self.app, 'mock_user')

    def mock_current_user(self, user):
        def decorator(f):
            def wrapped_function(*args, **kwargs):
                self.app.mock_user = user
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

    # Integration Tests for API Endpoints
    def test_sales_report_merchant(self):
        @self.mock_current_user(self.merchant_user)
        @self.mock_query_params({'period': 'weekly'})
        def _():
            response = self.client.get('/api/reports/sales?period=weekly')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['status'], 'success')
            self.assertIn('chart_data', response.json['report'])
            self.assertGreater(len(response.json['report']['chart_data']['labels']), 0)
            self.assertEqual(response.json['report']['total_quantity_sold'], 50)  # 20 + 30
            self.assertEqual(response.json['report']['total_revenue'], 840.0)  # 20*15 + 30*18

            # Test with date filtering
            start_date = (datetime.utcnow() - timedelta(days=5)).strftime('%Y-%m-%d')
            end_date = datetime.utcnow().strftime('%Y-%m-%d')
            @self.mock_query_params({'period': 'weekly', 'start_date': start_date, 'end_date': end_date})
            def __():
                response = self.client.get(f'/api/reports/sales?period=weekly&start_date={start_date}&end_date={end_date}')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json['status'], 'success')
                self.assertEqual(response.json['report']['total_quantity_sold'], 30)  # Only entry2
                self.assertEqual(response.json['report']['total_revenue'], 540.0)  # 30*18
            __()
        _()

    def test_sales_report_admin(self):
        @self.mock_current_user(self.admin_user)
        @self.mock_query_params({'period': 'monthly'})
        def _():
            response = self.client.get('/api/reports/sales?period=monthly')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['status'], 'success')
            self.assertIn('chart_data', response.json['report'])
            self.assertEqual(response.json['report']['total_quantity_sold'], 20)  # Only store1
            self.assertEqual(response.json['report']['total_revenue'], 300.0)  # 20*15
        _()

    def test_sales_report_invalid_period(self):
        @self.mock_current_user(self.merchant_user)
        @self.mock_query_params({'period': 'invalid'})
        def _():
            response = self.client.get('/api/reports/sales?period=invalid')
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json['status'], 'error')
            self.assertEqual(response.json['message'], 'Invalid period. Use weekly, monthly, or annual')
        _()

    def test_sales_report_invalid_date(self):
        @self.mock_current_user(self.merchant_user)
        @self.mock_query_params({'period': 'weekly', 'start_date': 'invalid', 'end_date': '2023-01-01'})
        def _():
            response = self.client.get('/api/reports/sales?period=weekly&start_date=invalid&end_date=2023-01-01')
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json['status'], 'error')
            self.assertEqual(response.json['message'], 'Invalid date format. Use YYYY-MM-DD')
        _()

        @self.mock_current_user(self.merchant_user)
        @self.mock_query_params({'period': 'weekly', 'start_date': '2023-12-01', 'end_date': '2023-01-01'})
        def _():
            response = self.client.get('/api/reports/sales?period=weekly&start_date=2023-12-01&end_date=2023-01-01')
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json['status'], 'error')
            self.assertEqual(response.json['message'], 'Start date must be before end date')
        _()

    def test_sales_report_no_token(self):
        if hasattr(self.app, 'mock_user'):
            delattr(self.app, 'mock_user')
        response = self.client.get('/api/reports/sales?period=weekly')
        self.assertEqual(response.status_code, 401)
        self.assertIn('Missing Authorization Header', response.json['msg'])

    def test_spoilage_report_admin(self):
        @self.mock_current_user(self.admin_user)
        @self.mock_query_params({})
        def _():
            response = self.client.get('/api/reports/spoilage')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['status'], 'success')
            self.assertIn('chart_data', response.json['report'])
            self.assertEqual(response.json['report']['total_spoilage'], 2)  # Only store1 entries
            self.assertEqual(len(response.json['report']['chart_data']['labels']), 1)
            self.assertEqual(response.json['report']['chart_data']['labels'][0], 'Test Category')
            self.assertEqual(response.json['report']['chart_data']['datasets'][0]['data'][0], 2)

            # Test with date filtering
            start_date = (datetime.utcnow() - timedelta(days=15)).strftime('%Y-%m-%d')
            end_date = (datetime.utcnow() - timedelta(days=5)).strftime('%Y-%m-%d')
            @self.mock_query_params({'start_date': start_date, 'end_date': end_date})
            def __():
                response = self.client.get(f'/api/reports/spoilage?start_date={start_date}&end_date={end_date}')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json['status'], 'success')
                self.assertEqual(response.json['report']['total_spoilage'], 2)  # entry1 is within range
            __()
        _()

    def test_spoilage_report_no_token(self):
        if hasattr(self.app, 'mock_user'):
            delattr(self.app, 'mock_user')
        response = self.client.get('/api/reports/spoilage')
        self.assertEqual(response.status_code, 401)
        self.assertIn('Missing Authorization Header', response.json['msg'])

    def test_payment_status_report_clerk(self):
        @self.mock_current_user(self.clerk_user)
        @self.mock_query_params({})
        def _():
            response = self.client.get('/api/reports/payment-status')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['status'], 'success')
            self.assertIn('chart_data', response.json['report'])
            self.assertEqual(response.json['report']['total_unpaid'], 200.0)  # 20 * 10.0
            self.assertEqual(response.json['report']['total_paid'], 0.0)  # Only store1 entries
            self.assertEqual(response.json['report']['chart_data']['labels'], ['Paid', 'Unpaid'])
            self.assertEqual(response.json['report']['chart_data']['datasets'][0]['data'], [0.0, 200.0])

            # Test with date filtering
            start_date = (datetime.utcnow() - timedelta(days=15)).strftime('%Y-%m-%d')
            end_date = (datetime.utcnow() - timedelta(days=5)).strftime('%Y-%m-%d')
            @self.mock_query_params({'start_date': start_date, 'end_date': end_date})
            def __():
                response = self.client.get(f'/api/reports/payment-status?start_date={start_date}&end_date={end_date}')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json['status'], 'success')
                self.assertEqual(response.json['report']['total_unpaid'], 200.0)  # entry1
                self.assertEqual(response.json['report']['total_paid'], 0.0)
                self.assertEqual(response.json['report']['chart_data']['datasets'][0]['data'], [0.0, 200.0])
            __()
        _()

    def test_payment_status_report_no_token(self):
        if hasattr(self.app, 'mock_user'):
            delattr(self.app, 'mock_user')
        response = self.client.get('/api/reports/payment-status')
        self.assertEqual(response.status_code, 401)
        self.assertIn('Missing Authorization Header', response.json['msg'])

    def test_store_comparison_merchant(self):
        @self.mock_current_user(self.merchant_user)
        @self.mock_query_params({})
        def _():
            response = self.client.get('/api/reports/store-comparison')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['status'], 'success')
            self.assertIn('chart_data', response.json['report'])
            self.assertEqual(len(response.json['report']['chart_data']['labels']), 2)
            self.assertEqual(response.json['report']['chart_data']['labels'], ['Store 1', 'Store 2'])
            self.assertEqual(response.json['report']['chart_data']['datasets'][0]['data'], [300.0, 540.0])
            self.assertEqual(response.json['report']['chart_data']['datasets'][1]['data'], [2, 3])

            # Test with date filtering
            start_date = (datetime.utcnow() - timedelta(days=5)).strftime('%Y-%m-%d')
            end_date = datetime.utcnow().strftime('%Y-%m-%d')
            @self.mock_query_params({'start_date': start_date, 'end_date': end_date})
            def __():
                response = self.client.get(f'/api/reports/store-comparison?start_date={start_date}&end_date={end_date}')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json['status'], 'success')
                self.assertEqual(len(response.json['report']['chart_data']['labels']), 1)
                self.assertEqual(response.json['report']['chart_data']['labels'], ['Store 2'])
            __()
        _()

    def test_store_comparison_unauthorized(self):
        @self.mock_current_user(self.admin_user)
        @self.mock_query_params({})
        def _():
            response = self.client.get('/api/reports/store-comparison')
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json['status'], 'error')
            self.assertEqual(response.json['message'], 'Unauthorized to view store comparison')
        _()

    def test_store_comparison_no_token(self):
        if hasattr(self.app, 'mock_user'):
            delattr(self.app, 'mock_user')
        response = self.client.get('/api/reports/store-comparison')
        self.assertEqual(response.status_code, 401)
        self.assertIn('Missing Authorization Header', response.json['msg'])

    def test_sales_chart_data(self):
        @self.mock_current_user(self.merchant_user)
        @self.mock_query_params({})
        def _():
            response = self.client.get('/api/reports/sales/chart-data')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['status'], 'success')
            self.assertIn('weekly', response.json['chart_data'])
            self.assertIn('monthly', response.json['chart_data'])
            self.assertIn('annual', response.json['chart_data'])
            self.assertGreater(len(response.json['chart_data']['weekly']['labels']), 0)
            self.assertEqual(response.json['chart_data']['weekly']['datasets'][0]['data'][0], 840.0)
            self.assertEqual(response.json['chart_data']['weekly']['datasets'][1]['data'][0], 5)

            # Test with date filtering
            start_date = (datetime.utcnow() - timedelta(days=5)).strftime('%Y-%m-%d')
            end_date = datetime.utcnow().strftime('%Y-%m-%d')
            @self.mock_query_params({'start_date': start_date, 'end_date': end_date})
            def __():
                response = self.client.get(f'/api/reports/sales/chart-data?start_date={start_date}&end_date={end_date}')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json['status'], 'success')
                self.assertEqual(len(response.json['chart_data']['weekly']['labels']), 1)
                self.assertEqual(response.json['chart_data']['weekly']['datasets'][0]['data'][0], 540.0)
            __()
        _()

    def test_sales_chart_data_no_token(self):
        if hasattr(self.app, 'mock_user'):
            delattr(self.app, 'mock_user')
        response = self.client.get('/api/reports/sales/chart-data')
        self.assertEqual(response.status_code, 401)
        self.assertIn('Missing Authorization Header', response.json['msg'])

    def test_clerk_performance(self):
        @self.mock_current_user(self.admin_user)
        @self.mock_query_params({'clerk_id': str(self.clerk_user.id)})
        def _():
            response = self.client.get(f'/api/reports/clerk-performance?clerk_id={self.clerk_user.id}')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['status'], 'success')
            self.assertEqual(response.json['report']['total_entries'], 1)  # Only store1 entries
            self.assertEqual(response.json['report']['total_spoiled'], 2)
            self.assertEqual(response.json['report']['total_sales'], 300.0)  # 20*15

            # Test with date filtering
            start_date = (datetime.utcnow() - timedelta(days=5)).strftime('%Y-%m-%d')
            end_date = datetime.utcnow().strftime('%Y-%m-%d')
            @self.mock_query_params({'clerk_id': str(self.clerk_user.id), 'start_date': start_date, 'end_date': end_date})
            def __():
                response = self.client.get(f'/api/reports/clerk-performance?clerk_id={self.clerk_user.id}&start_date={start_date}&end_date={end_date}')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json['status'], 'success')
                self.assertEqual(response.json['report']['total_entries'], 0)  # No entries in date range for store1
                self.assertEqual(response.json['report']['total_spoiled'], 0)
                self.assertEqual(response.json['report']['total_sales'], 0.0)
            __()
        _()

    def test_clerk_performance_unauthorized(self):
        @self.mock_current_user(self.clerk_user)
        @self.mock_query_params({'clerk_id': str(self.clerk_user.id)})
        def _():
            response = self.client.get(f'/api/reports/clerk-performance?clerk_id={self.clerk_user.id}')
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json['status'], 'error')
            self.assertEqual(response.json['message'], 'Unauthorized to view clerk performance')
        _()

    def test_clerk_performance_invalid_clerk_id(self):
        @self.mock_current_user(self.admin_user)
        @self.mock_query_params({'clerk_id': '999'})
        def _():
            response = self.client.get('/api/reports/clerk-performance?clerk_id=999')
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json['status'], 'error')
            self.assertEqual(response.json['message'], 'Clerk not found')
        _()

    def test_clerk_performance_no_clerk_id(self):
        @self.mock_current_user(self.admin_user)
        @self.mock_query_params({})
        def _():
            response = self.client.get('/api/reports/clerk-performance')
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json['status'], 'error')
            self.assertEqual(response.json['message'], 'Clerk ID is required')
        _()

    def test_clerk_performance_no_token(self):
        if hasattr(self.app, 'mock_user'):
            delattr(self.app, 'mock_user')
        response = self.client.get(f'/api/reports/clerk-performance?clerk_id={self.clerk_user.id}')
        self.assertEqual(response.status_code, 401)
        self.assertIn('Missing Authorization Header', response.json['msg'])

    def test_export_sales_pdf(self):
        @self.mock_current_user(self.merchant_user)
        @self.mock_query_params({'type': 'sales', 'format': 'pdf'})
        def _():
            response = self.client.get('/api/reports/export?type=sales&format=pdf')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content_type, 'application/pdf')
            self.assertEqual(response.headers['Content-Disposition'], 'attachment; filename=sales_report.pdf')
        _()

    def test_export_spoilage_excel(self):
        @self.mock_current_user(self.merchant_user)
        @self.mock_query_params({'type': 'spoilage', 'format': 'excel'})
        def _():
            response = self.client.get('/api/reports/export?type=spoilage&format=excel')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content_type, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            self.assertEqual(response.headers['Content-Disposition'], 'attachment; filename=spoilage_report.xlsx')
        _()

    def test_export_payment_status_pdf(self):
        @self.mock_current_user(self.merchant_user)
        @self.mock_query_params({'type': 'payment-status', 'format': 'pdf'})
        def _():
            response = self.client.get('/api/reports/export?type=payment-status&format=pdf')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content_type, 'application/pdf')
            self.assertEqual(response.headers['Content-Disposition'], 'attachment; filename=payment-status_report.pdf')
        _()

    def test_export_invalid_type(self):
        @self.mock_current_user(self.merchant_user)
        @self.mock_query_params({'type': 'invalid', 'format': 'pdf'})
        def _():
            response = self.client.get('/api/reports/export?type=invalid&format=pdf')
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json['status'], 'error')
            self.assertEqual(response.json['message'], 'Invalid report type. Use sales, spoilage, or payment-status')
        _()

    def test_export_invalid_format(self):
        @self.mock_current_user(self.merchant_user)
        @self.mock_query_params({'type': 'sales', 'format': 'invalid'})
        def _():
            response = self.client.get('/api/reports/export?type=sales&format=invalid')
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json['status'], 'error')
            self.assertEqual(response.json['message'], 'Invalid format. Use pdf or excel')
        _()

    def test_export_no_token(self):
        if hasattr(self.app, 'mock_user'):
            delattr(self.app, 'mock_user')
        response = self.client.get('/api/reports/export?type=sales&format=pdf')
        self.assertEqual(response.status_code, 401)
        self.assertIn('Missing Authorization Header', response.json['msg'])

    def test_sales_trend_chart(self):
        @self.mock_current_user(self.merchant_user)
        @self.mock_query_params({'period': 'monthly'})
        def _():
            response = self.client.get('/api/reports/chart-data/sales-trend?period=monthly')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['status'], 'success')
            self.assertIn('chart_data', response.json)
            self.assertGreater(len(response.json['chart_data']['labels']), 0)
            self.assertEqual(response.json['chart_data']['datasets'][0]['data'][0], 840.0)

            # Test with date filtering
            start_date = (datetime.utcnow() - timedelta(days=5)).strftime('%Y-%m-%d')
            end_date = datetime.utcnow().strftime('%Y-%m-%d')
            @self.mock_query_params({'period': 'monthly', 'start_date': start_date, 'end_date': end_date})
            def __():
                response = self.client.get(f'/api/reports/chart-data/sales-trend?period=monthly&start_date={start_date}&end_date={end_date}')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json['status'], 'success')
                self.assertEqual(len(response.json['chart_data']['labels']), 1)
                self.assertEqual(response.json['chart_data']['datasets'][0]['data'][0], 540.0)
            __()
        _()

    def test_sales_trend_chart_invalid_period(self):
        @self.mock_current_user(self.merchant_user)
        @self.mock_query_params({'period': 'invalid'})
        def _():
            response = self.client.get('/api/reports/chart-data/sales-trend?period=invalid')
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json['status'], 'error')
            self.assertEqual(response.json['message'], 'Invalid period. Use weekly, monthly, or annual')
        _()

    def test_sales_trend_chart_no_token(self):
        if hasattr(self.app, 'mock_user'):
            delattr(self.app, 'mock_user')
        response = self.client.get('/api/reports/chart-data/sales-trend?period=monthly')
        self.assertEqual(response.status_code, 401)
        self.assertIn('Missing Authorization Header', response.json['msg'])

    def test_spoilage_by_category(self):
        @self.mock_current_user(self.merchant_user)
        @self.mock_query_params({})
        def _():
            response = self.client.get('/api/reports/chart-data/spoilage-by-category')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['status'], 'success')
            self.assertIn('chart_data', response.json)
            self.assertEqual(len(response.json['chart_data']['labels']), 1)
            self.assertEqual(response.json['chart_data']['labels'][0], 'Test Category')
            self.assertEqual(response.json['chart_data']['datasets'][0]['data'][0], 5)

            # Test with date filtering
            start_date = (datetime.utcnow() - timedelta(days=5)).strftime('%Y-%m-%d')
            end_date = datetime.utcnow().strftime('%Y-%m-%d')
            @self.mock_query_params({'start_date': start_date, 'end_date': end_date})
            def __():
                response = self.client.get(f'/api/reports/chart-data/spoilage-by-category?start_date={start_date}&end_date={end_date}')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json['status'], 'success')
                self.assertEqual(len(response.json['chart_data']['labels']), 1)
                self.assertEqual(response.json['chart_data']['datasets'][0]['data'][0], 3)
            __()
        _()

    def test_spoilage_by_category_no_token(self):
        if hasattr(self.app, 'mock_user'):
            delattr(self.app, 'mock_user')
        response = self.client.get('/api/reports/chart-data/spoilage-by-category')
        self.assertEqual(response.status_code, 401)
        self.assertIn('Missing Authorization Header', response.json['msg'])

if __name__ == '__main__':
    unittest.main()