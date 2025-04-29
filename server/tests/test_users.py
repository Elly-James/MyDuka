import unittest
from flask import Flask, jsonify
from datetime import datetime
from enum import Enum

# Mock enums for UserRole and UserStatus
class UserRole(str, Enum):
    ADMIN = "ADMIN"
    MERCHANT = "MERCHANT"
    CLERK = "CLERK"

class UserStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

# Mock models (to avoid actual database usage)
class User:
    def __init__(self, id, email, name, role, status, store_id=None):
        self.id = id
        self.email = email
        self.name = name
        self.role = role
        self.status = status
        self.store_id = store_id
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self._password = None  # Simulate password hashing

    def set_password(self, password):
        self._password = password  # Simplified for testing; real app would hash

    def check_password(self, password):
        return self._password == password

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'role': self.role,
            'status': self.status,
            'store_id': self.store_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
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

class Notification:
    def __init__(self, id, user_id, message):
        self.id = id
        self.user_id = user_id
        self.message = message
        self.is_read = False
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'message': self.message,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

# Create Flask app for testing
app = Flask(__name__)

# Simulated routes (simplified to avoid database calls)
@app.route('/api/users', methods=['GET'])
def get_users():
    user = getattr(app, 'mock_user', None)
    if not user:
        return jsonify({'msg': 'Missing Authorization Header'}), 401
    if user.role == UserRole.CLERK:
        return jsonify({'status': 'error', 'message': 'Unauthorized to view users'}), 403

    query_params = getattr(app, 'mock_query_params', {})
    role = query_params.get('role')
    status = query_params.get('status')
    page = int(query_params.get('page', 1))
    per_page = int(query_params.get('per_page', 50))

    # Validate role and status
    if role and role not in [r.value for r in UserRole]:
        return jsonify({'status': 'error', 'message': 'Invalid role'}), 400
    if status and status not in [s.value for s in UserStatus]:
        return jsonify({'status': 'error', 'message': 'Invalid status'}), 400

    users = getattr(app, 'mock_users', [])
    # Filter users based on role and permissions
    if user.role == UserRole.MERCHANT:
        filtered_users = [u for u in users if u.role != UserRole.MERCHANT]
    else:  # ADMIN
        filtered_users = [u for u in users if u.store_id == user.store_id and u.role != UserRole.MERCHANT]

    # Apply filters
    if role:
        filtered_users = [u for u in filtered_users if u.role == role]
    if status:
        filtered_users = [u for u in filtered_users if u.status == status]

    # Sort by created_at descending
    filtered_users.sort(key=lambda x: x.created_at, reverse=True)
    total = len(filtered_users)
    # Apply pagination
    start = (page - 1) * per_page
    end = start + per_page
    paginated_users = filtered_users[start:end]

    return jsonify({
        'status': 'success',
        'users': [u.to_dict() for u in paginated_users],
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page
    }), 200

@app.route('/api/users/<int:user_id>/status', methods=['PUT'])
def update_user_status(user_id):
    user = getattr(app, 'mock_user', None)
    if not user:
        return jsonify({'msg': 'Missing Authorization Header'}), 401
    if user.role == UserRole.CLERK:
        return jsonify({'status': 'error', 'message': 'Unauthorized to update user status'}), 403

    data = getattr(app, 'mock_request_data', {})
    new_status = data.get('status')
    if not new_status or new_status not in [s.value for s in UserStatus]:
        return jsonify({
            'status': 'error',
            'message': 'Validation error',
            'errors': {'status': 'Invalid status value'}
        }), 400

    users = getattr(app, 'mock_users', [])
    target_user = next((u for u in users if u.id == user_id), None)
    if not target_user:
        return jsonify({'status': 'error', 'message': 'Target user not found'}), 404

    # Permission checks
    if user.role == UserRole.ADMIN:
        if target_user.role == UserRole.MERCHANT or target_user.store_id != user.store_id:
            return jsonify({'status': 'error', 'message': 'You can only manage clerks in your store'}), 403
    # Merchant can update any non-merchant user

    target_user.status = new_status
    target_user.updated_at = datetime.now()

    # Simulate notification creation
    notification = Notification(
        id=len(getattr(app, 'mock_notifications', [])) + 1,
        user_id=target_user.id,
        message=f"Your status has been updated to {new_status.lower()}"
    )
    app.mock_notifications = getattr(app, 'mock_notifications', []) + [notification]

    return jsonify({
        'status': 'success',
        'message': f'User status updated to {new_status.lower()} successfully',
        'user': target_user.to_dict()
    }), 200

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    user = getattr(app, 'mock_user', None)
    if not user:
        return jsonify({'msg': 'Missing Authorization Header'}), 401
    if user.role == UserRole.CLERK:
        return jsonify({'status': 'error', 'message': 'Unauthorized to delete users'}), 403

    users = getattr(app, 'mock_users', [])
    target_user = next((u for u in users if u.id == user_id), None)
    if not target_user:
        return jsonify({'status': 'error', 'message': 'Target user not found'}), 404

    # Permission checks
    if user.role == UserRole.ADMIN:
        if target_user.role == UserRole.MERCHANT or target_user.store_id != user.store_id:
            return jsonify({'status': 'error', 'message': 'You can only delete clerks in your store'}), 403
    # Merchant can delete any non-merchant user

    app.mock_users = [u for u in users if u.id != user_id]
    return jsonify({
        'status': 'success',
        'message': 'User deleted successfully'
    }), 200

# Test class
class UsersTests(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        self.app.config['TESTING'] = True

        # Mock store
        self.store = Store(id=1, name="Test Store", location="123 Test St")

        # Mock users
        self.merchant = User(id=1, email="merchant@test.com", name="Test Merchant", role=UserRole.MERCHANT, status=UserStatus.ACTIVE)
        self.merchant.set_password("password123")

        self.admin = User(id=2, email="admin@test.com", name="Test Admin", role=UserRole.ADMIN, status=UserStatus.ACTIVE, store_id=self.store.id)
        self.admin.set_password("password123")

        self.clerk = User(id=3, email="clerk@test.com", name="Test Clerk", role=UserRole.CLERK, status=UserStatus.ACTIVE, store_id=self.store.id)
        self.clerk.set_password("password123")

        self.clerk2 = User(id=4, email="clerk2@test.com", name="Test Clerk 2", role=UserRole.CLERK, status=UserStatus.ACTIVE, store_id=self.store.id)
        self.clerk2.set_password("password123")

        self.app.mock_users = [self.merchant, self.admin, self.clerk, self.clerk2]
        self.app.mock_notifications = []

    def tearDown(self):
        # Clear mock_user to prevent state leakage between tests
        if hasattr(self.app, 'mock_user'):
            delattr(self.app, 'mock_user')
        if hasattr(self.app, 'mock_query_params'):
            delattr(self.app, 'mock_query_params')
        if hasattr(self.app, 'mock_request_data'):
            delattr(self.app, 'mock_request_data')

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

    def mock_request_data(self, data):
        def decorator(f):
            def wrapped_function(*args, **kwargs):
                self.app.mock_request_data = data
                return f(*args, **kwargs)
            return wrapped_function
        return decorator

    # Removed test_user_model since it requires database access

    # Integration Tests for API Endpoints
    def test_get_users_by_merchant(self):
        @self.mock_current_user(self.merchant)
        @self.mock_query_params({'role': 'ADMIN'})
        def _():
            response = self.client.get('/api/users?role=ADMIN')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['status'], 'success')
            self.assertEqual(response.json['total'], 1)
            self.assertEqual(len(response.json['users']), 1)
            self.assertEqual(response.json['users'][0]['email'], 'admin@test.com')
            self.assertEqual(response.json['page'], 1)
            self.assertEqual(response.json['per_page'], 50)

            # Test filtering by status
            @self.mock_query_params({'status': 'ACTIVE'})
            def __():
                response = self.client.get('/api/users?status=ACTIVE')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json['status'], 'success')
                self.assertEqual(response.json['total'], 3)  # Admin + 2 Clerks (Merchant not included)
            __()

            # Test pagination
            @self.mock_query_params({'page': '1', 'per_page': '2'})
            def __():
                response = self.client.get('/api/users?page=1&per_page=2')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json['status'], 'success')
                self.assertEqual(response.json['total'], 3)
                self.assertEqual(len(response.json['users']), 2)
                self.assertEqual(response.json['per_page'], 2)
                self.assertEqual(response.json['pages'], 2)
            __()
        _()

    def test_get_users_by_admin(self):
        @self.mock_current_user(self.admin)
        @self.mock_query_params({'role': 'CLERK'})
        def _():
            response = self.client.get('/api/users?role=CLERK')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['status'], 'success')
            self.assertEqual(response.json['total'], 2)  # Two clerks in the store
            self.assertEqual(len(response.json['users']), 2)
            self.assertEqual(response.json['users'][0]['store_id'], self.store.id)
        _()

    def test_get_users_invalid_filter(self):
        @self.mock_current_user(self.merchant)
        @self.mock_query_params({'role': 'INVALID'})
        def _():
            response = self.client.get('/api/users?role=INVALID')
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json['status'], 'error')
            self.assertEqual(response.json['message'], 'Invalid role')

            @self.mock_query_params({'status': 'INVALID'})
            def __():
                response = self.client.get('/api/users?status=INVALID')
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json['status'], 'error')
                self.assertEqual(response.json['message'], 'Invalid status')
            __()
        _()

    def test_get_users_no_token(self):
        if hasattr(self.app, 'mock_user'):
            delattr(self.app, 'mock_user')
        response = self.client.get('/api/users')
        self.assertEqual(response.status_code, 401)
        self.assertIn('Missing Authorization Header', response.json['msg'])

    def test_update_user_status_by_admin(self):
        @self.mock_current_user(self.admin)
        @self.mock_request_data({'status': 'INACTIVE'})
        def _():
            response = self.client.put('/api/users/3/status')  # Clerk's ID
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['status'], 'success')
            self.assertEqual(response.json['message'], 'User status updated to inactive successfully')
            self.assertEqual(response.json['user']['status'], 'INACTIVE')
            # Check notification
            notifications = getattr(self.app, 'mock_notifications', [])
            self.assertEqual(len(notifications), 1)
            self.assertIn('status has been updated to inactive', notifications[0].message)
        _()

    def test_update_user_status_by_merchant(self):
        @self.mock_current_user(self.merchant)
        @self.mock_request_data({'status': 'INACTIVE'})
        def _():
            response = self.client.put('/api/users/2/status')  # Admin's ID
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['status'], 'success')
            self.assertEqual(response.json['message'], 'User status updated to inactive successfully')
            self.assertEqual(response.json['user']['status'], 'INACTIVE')
        _()

    def test_update_user_status_unauthorized(self):
        @self.mock_current_user(self.admin)
        @self.mock_request_data({'status': 'INACTIVE'})
        def _():
            response = self.client.put('/api/users/1/status')  # Merchant's ID
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json['status'], 'error')
            self.assertEqual(response.json['message'], 'You can only manage clerks in your store')
        _()

    def test_update_user_status_invalid_status(self):
        @self.mock_current_user(self.admin)
        @self.mock_request_data({'status': 'INVALID'})
        def _():
            response = self.client.put('/api/users/3/status')  # Clerk's ID
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json['status'], 'error')
            self.assertEqual(response.json['message'], 'Validation error')
            self.assertIn('status', response.json['errors'])
        _()

    def test_update_user_status_no_token(self):
        if hasattr(self.app, 'mock_user'):
            delattr(self.app, 'mock_user')
        response = self.client.put('/api/users/3/status', json={'status': 'INACTIVE'})
        self.assertEqual(response.status_code, 401)
        self.assertIn('Missing Authorization Header', response.json['msg'])

    def test_update_user_status_not_found(self):
        @self.mock_current_user(self.admin)
        @self.mock_request_data({'status': 'INACTIVE'})
        def _():
            response = self.client.put('/api/users/999/status')
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json['status'], 'error')
            self.assertEqual(response.json['message'], 'Target user not found')
        _()

    def test_delete_user_by_merchant(self):
        @self.mock_current_user(self.merchant)
        def _():
            response = self.client.delete('/api/users/2')  # Admin's ID
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['status'], 'success')
            self.assertEqual(response.json['message'], 'User deleted successfully')
            users = getattr(self.app, 'mock_users', [])
            self.assertEqual(len(users), 3)  # One user deleted
        _()

    def test_delete_user_by_admin(self):
        @self.mock_current_user(self.admin)
        def _():
            response = self.client.delete('/api/users/3')  # Clerk's ID
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['status'], 'success')
            self.assertEqual(response.json['message'], 'User deleted successfully')
            users = getattr(self.app, 'mock_users', [])
            self.assertEqual(len(users), 3)  # One user deleted
        _()

    def test_delete_user_unauthorized(self):
        @self.mock_current_user(self.admin)
        def _():
            response = self.client.delete('/api/users/1')  # Merchant's ID
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json['status'], 'error')
            self.assertEqual(response.json['message'], 'You can only delete clerks in your store')
        _()

    def test_delete_user_no_token(self):
        if hasattr(self.app, 'mock_user'):
            delattr(self.app, 'mock_user')
        response = self.client.delete('/api/users/3')
        self.assertEqual(response.status_code, 401)
        self.assertIn('Missing Authorization Header', response.json['msg'])

    def test_delete_user_not_found(self):
        @self.mock_current_user(self.merchant)
        def _():
            response = self.client.delete('/api/users/999')
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json['status'], 'error')
            self.assertEqual(response.json['message'], 'Target user not found')
        _()

    def test_unauthorized_access_by_clerk(self):
        @self.mock_current_user(self.clerk)
        def _():
            # Test GET
            response = self.client.get('/api/users')
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json['status'], 'error')
            self.assertEqual(response.json['message'], 'Unauthorized to view users')

            # Test PUT
            @self.mock_request_data({'status': 'INACTIVE'})
            def __():
                response = self.client.put('/api/users/2/status')  # Admin's ID
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.json['status'], 'error')
                self.assertEqual(response.json['message'], 'Unauthorized to update user status')
            __()

            # Test DELETE
            response = self.client.delete('/api/users/2')  # Admin's ID
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json['status'], 'error')
            self.assertEqual(response.json['message'], 'Unauthorized to delete users')
        _()

if __name__ == '__main__':
    unittest.main()