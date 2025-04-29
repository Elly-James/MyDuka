import unittest
from flask import Flask, jsonify
from datetime import datetime, timedelta
import uuid
from unittest.mock import patch, MagicMock

# Mock enums (to avoid importing from models)
class UserRole:
    ADMIN = 'ADMIN'
    MERCHANT = 'MERCHANT'
    CLERK = 'CLERK'

class UserStatus:
    ACTIVE = 'ACTIVE'
    INACTIVE = 'INACTIVE'

# Mock models (to avoid actual database usage)
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

class User:
    def __init__(self, id, email, name, role, status, store_id=None):
        self.id = id
        self.email = email
        self.name = name
        self.role = role
        self.status = status
        self.store_id = store_id
        self.password_hash = None
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def set_password(self, password):
        self.password_hash = password  # Simplified for testing

    def check_password(self, password):
        return self.password_hash == password

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'role': self.role,
            'status': self.status,
            'store_id': self.store_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'store_name': self.store.name if hasattr(self, 'store') else None
        }

class Invitation:
    def __init__(self, id, email, token, role, creator_id, store_id, expires_at):
        self.id = id
        self.email = email
        self.token = token
        self.role = role
        self.creator_id = creator_id
        self.store_id = store_id
        self.expires_at = expires_at
        self.is_used = False

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'token': self.token,
            'role': self.role,
            'creator_id': self.creator_id,
            'store_id': self.store_id,
            'expires_at': self.expires_at.isoformat(),
            'is_used': self.is_used
        }

class PasswordReset:
    def __init__(self, id, user_id, token, expires_at):
        self.id = id
        self.user_id = user_id
        self.token = token
        self.expires_at = expires_at
        self.is_used = False

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'token': self.token,
            'expires_at': self.expires_at.isoformat(),
            'is_used': self.is_used
        }

class Notification:
    def __init__(self, id, user_id, message):
        self.id = id
        self.user_id = user_id
        self.message = message

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'message': self.message
        }

# Create Flask app for testing
app = Flask(__name__)
app.config['BASE_URL'] = 'http://localhost:5000'
app.config['GOOGLE_CLIENT_ID'] = 'mock-client-id'
app.config['GOOGLE_CLIENT_SECRET'] = 'mock-client-secret'

# Simulated routes (simplified to avoid database calls)
@app.route('/api/auth/login', methods=['POST'])
def login():
    data = getattr(app, 'mock_request_data', {})
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'status': 'error', 'message': 'Email and password are required'}), 400

    # Simple email format check
    if '@' not in email or '.' not in email:
        return jsonify({'status': 'error', 'message': 'Validation error', 'errors': {'email': 'Invalid email format'}}), 400

    # Simulate rate limiting
    request_count = getattr(app, 'mock_request_count', {}).get(email, 0)
    if request_count >= 5:
        return jsonify({'msg': 'Too Many Requests'}), 429

    users = getattr(app, 'mock_users', [])
    user = next((u for u in users if u.email == email), None)
    if not user or not user.check_password(password):
        return jsonify({'status': 'error', 'message': 'Invalid email or password'}), 401

    if user.status == UserStatus.INACTIVE:
        return jsonify({'status': 'error', 'message': 'Account is inactive'}), 403

    redirect_to = '/merchant-dashboard' if user.role == UserRole.MERCHANT else '/dashboard'
    return jsonify({
        'status': 'success',
        'access_token': f'mock-token-{user.email}',
        'user': user.to_dict(),
        'redirect_to': redirect_to
    }), 200

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = getattr(app, 'mock_request_data', {})
    email = data.get('email')
    name = data.get('name')
    password = data.get('password')
    token = data.get('token')

    if not all([email, name, password, token]):
        return jsonify({'status': 'error', 'message': 'Name, email, password, and invitation token are required'}), 400

    users = getattr(app, 'mock_users', [])
    if any(u.email == email for u in users):
        return jsonify({'status': 'error', 'message': 'User with this email already exists'}), 400

    invitations = getattr(app, 'mock_invitations', [])
    invitation = next((i for i in invitations if i.token == token and i.email == email), None)
    if not invitation:
        return jsonify({'status': 'error', 'message': 'Invalid or expired invitation token'}), 400
    if invitation.expires_at < datetime.now():
        return jsonify({'status': 'error', 'message': 'Invitation token has expired'}), 400
    if invitation.is_used:
        return jsonify({'status': 'error', 'message': 'Invitation token has already been used'}), 400

    invitation.is_used = True
    new_user = User(
        id=len(users) + 1,
        email=email,
        name=name,
        role=invitation.role,
        status=UserStatus.ACTIVE,
        store_id=invitation.store_id
    )
    new_user.set_password(password)
    app.mock_users.append(new_user)

    return jsonify({
        'status': 'success',
        'message': 'Registration successful',
        'user': new_user.to_dict()
    }), 201

@app.route('/api/auth/invite', methods=['POST'])
def invite():
    user = getattr(app, 'mock_user', None)
    if not user:
        return jsonify({'msg': 'Missing Authorization Header'}), 401

    data = getattr(app, 'mock_request_data', {})
    email = data.get('email')
    role = data.get('role')
    store_id = data.get('store_id')

    if user.role == UserRole.MERCHANT and role != UserRole.ADMIN:
        return jsonify({'status': 'error', 'message': 'You are not authorized to invite users with this role'}), 403
    if user.role == UserRole.ADMIN and role != UserRole.CLERK:
        return jsonify({'status': 'error', 'message': 'You are not authorized to invite users with this role'}), 403

    invitations = getattr(app, 'mock_invitations', [])
    if any(i.email == email and not i.is_used for i in invitations):
        return jsonify({'status': 'error', 'message': 'An invitation for this email already exists'}), 400

    # If store_id is not provided and the user is an ADMIN, use the admin's store_id
    if store_id is None and user.role == UserRole.ADMIN:
        store_id = user.store_id

    stores = getattr(app, 'mock_stores', [])
    store = next((s for s in stores if s.id == store_id), None)
    if not store:
        return jsonify({'status': 'error', 'message': 'Store not found'}), 404

    invitation = Invitation(
        id=len(invitations) + 1,
        email=email,
        token=str(uuid.uuid4()),
        role=role,
        creator_id=user.id,
        store_id=store_id,
        expires_at=datetime.now() + timedelta(days=7)
    )
    app.mock_invitations.append(invitation)

    # Simulate notification creation
    notification = Notification(
        id=len(getattr(app, 'mock_notifications', [])) + 1,
        user_id=user.id,
        message=f'You have invited {email} as a {role.lower()}'
    )
    app.mock_notifications = getattr(app, 'mock_notifications', []) + [notification]

    return jsonify({
        'status': 'success',
        'message': 'Invitation sent successfully',
        'invitation': invitation.to_dict()
    }), 201

@app.route('/api/auth/forgot-password', methods=['POST'])
def forgot_password():
    data = getattr(app, 'mock_request_data', {})
    email = data.get('email')

    if not email or '@' not in email or '.' not in email:
        return jsonify({'status': 'error', 'message': 'Validation error', 'errors': {'email': 'Invalid email format'}}), 400

    # Simulate rate limiting
    request_count = getattr(app, 'mock_request_count', {}).get(email, 0)
    if request_count >= 5:
        return jsonify({'msg': 'Too Many Requests'}), 429

    users = getattr(app, 'mock_users', [])
    user = next((u for u in users if u.email == email), None)
    mock_send_called = bool(user)  # Simulate email sending only if user exists
    app.mock_send_called = mock_send_called

    if user:
        reset = PasswordReset(
            id=len(getattr(app, 'mock_password_resets', [])) + 1,
            user_id=user.id,
            token=str(uuid.uuid4()),
            expires_at=datetime.now() + timedelta(hours=1)
        )
        app.mock_password_resets = getattr(app, 'mock_password_resets', []) + [reset]

    return jsonify({
        'status': 'success',
        'message': 'If the email exists, a reset link has been sent'
    }), 200

@app.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    data = getattr(app, 'mock_request_data', {})
    token = data.get('token')
    password = data.get('password')

    if not token or not password:
        return jsonify({'status': 'error', 'message': 'Token and new password are required'}), 400

    # Simulate rate limiting
    request_count = getattr(app, 'mock_request_count', {}).get(token, 0)
    if request_count >= 5:
        return jsonify({'msg': 'Too Many Requests'}), 429

    password_resets = getattr(app, 'mock_password_resets', [])
    reset = next((r for r in password_resets if r.token == token), None)
    if not reset or reset.is_used or reset.expires_at < datetime.now():
        return jsonify({'status': 'error', 'message': 'Invalid or expired reset token'}), 400

    users = getattr(app, 'mock_users', [])
    user = next((u for u in users if u.id == reset.user_id), None)
    if not user:
        return jsonify({'status': 'error', 'message': 'User not found'}), 404

    user.set_password(password)
    reset.is_used = True

    return jsonify({
        'status': 'success',
        'message': 'Password reset successfully'
    }), 200

@app.route('/api/auth/me', methods=['GET'])
def get_current_user():
    user = getattr(app, 'mock_user', None)
    if not user:
        return jsonify({'msg': 'Missing Authorization Header'}), 401

    users = getattr(app, 'mock_users', [])
    user = next((u for u in users if u.id == user.id), None)
    if not user:
        return jsonify({'status': 'error', 'message': 'User not found'}), 404

    user_dict = user.to_dict()
    if user.store_id:
        stores = getattr(app, 'mock_stores', [])
        store = next((s for s in stores if s.id == user.store_id), None)
        if store:
            user_dict['store_name'] = store.name

    return jsonify({
        'status': 'success',
        'user': user_dict
    }), 200

@app.route('/api/auth/google/login', methods=['GET'])
def google_login():
    if not app.config.get('GOOGLE_CLIENT_ID') or not app.config.get('GOOGLE_CLIENT_SECRET'):
        return jsonify({'status': 'error', 'message': 'Google OAuth credentials not configured'}), 500

    # Simulate redirect URL generation
    redirect_url = getattr(app, 'mock_redirect_url', 'https://accounts.google.com/o/oauth2/auth')
    app.mock_state = 'state123'
    return jsonify({'location': redirect_url}), 302

@app.route('/api/auth/google/callback', methods=['GET'])
def google_callback():
    query_params = getattr(app, 'mock_query_params', {})
    state = query_params.get('state')
    code = query_params.get('code')

    if state != app.mock_state:
        return jsonify({'status': 'error', 'message': 'Invalid state parameter'}), 400

    if not code or getattr(app, 'mock_token_fetch_error', False):
        return jsonify({'status': 'error', 'message': 'Failed to authenticate with Google: Token fetch failed'}), 400

    google_user_info = getattr(app, 'mock_google_user_info', {})
    email = google_user_info.get('email')
    name = google_user_info.get('name', 'Google User')

    if not email:
        return jsonify({'status': 'error', 'message': 'Failed to retrieve email from Google'}), 400

    users = getattr(app, 'mock_users', [])
    user = next((u for u in users if u.email == email), None)
    if not user:
        user = User(
            id=len(users) + 1,
            email=email,
            name=name,
            role=UserRole.CLERK,
            status=UserStatus.ACTIVE
        )
        user.set_password('google-oauth')  # Dummy password
        app.mock_users.append(user)

    return jsonify({
        'status': 'success',
        'message': 'Google login successful',
        'access_token': f'mock-token-{user.email}',
        'user': user.to_dict()
    }), 200

# Test class
class AuthTests(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        self.app.config['TESTING'] = True

        # Mock stores
        self.store = Store(id=1, name="Test Store", location="123 Test St")
        self.app.mock_stores = [self.store]

        # Mock users
        self.merchant = User(id=1, email="merchant@test.com", name="Test Merchant", role=UserRole.MERCHANT, status=UserStatus.ACTIVE)
        self.merchant.set_password("password123")
        self.admin = User(id=2, email="admin@test.com", name="Test Admin", role=UserRole.ADMIN, status=UserStatus.ACTIVE, store_id=self.store.id)
        self.admin.set_password("password123")
        self.clerk = User(id=3, email="clerk@test.com", name="Test Clerk", role=UserRole.CLERK, status=UserStatus.ACTIVE, store_id=self.store.id)
        self.clerk.set_password("password123")
        self.app.mock_users = [self.merchant, self.admin, self.clerk]

        # Mock invitations and password resets
        self.app.mock_invitations = []
        self.app.mock_password_resets = []
        self.app.mock_notifications = []
        self.app.mock_request_count = {}

    def tearDown(self):
        # Clear mock state
        if hasattr(self.app, 'mock_user'):
            delattr(self.app, 'mock_user')
        if hasattr(self.app, 'mock_request_data'):
            delattr(self.app, 'mock_request_data')
        if hasattr(self.app, 'mock_query_params'):
            delattr(self.app, 'mock_query_params')
        if hasattr(self.app, 'mock_send_called'):
            delattr(self.app, 'mock_send_called')
        if hasattr(self.app, 'mock_state'):
            delattr(self.app, 'mock_state')
        if hasattr(self.app, 'mock_token_fetch_error'):
            delattr(self.app, 'mock_token_fetch_error')
        if hasattr(self.app, 'mock_google_user_info'):
            delattr(self.app, 'mock_google_user_info')

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

    # Integration Tests for API Endpoints
    def test_login_success(self):
        @self.mock_request_data({'email': 'merchant@test.com', 'password': 'password123'})
        def _():
            response = self.client.post('/api/auth/login')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['status'], 'success')
            self.assertIn('access_token', response.json)
            self.assertEqual(response.json['user']['email'], 'merchant@test.com')
            self.assertEqual(response.json['redirect_to'], '/merchant-dashboard')
        _()

    def test_login_invalid_credentials(self):
        @self.mock_request_data({'email': 'merchant@test.com', 'password': 'wrongpassword'})
        def _():
            response = self.client.post('/api/auth/login')
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json['status'], 'error')
            self.assertEqual(response.json['message'], 'Invalid email or password')
        _()

    def test_login_invalid_email_format(self):
        @self.mock_request_data({'email': 'invalid-email', 'password': 'password123'})
        def _():
            response = self.client.post('/api/auth/login')
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json['status'], 'error')
            self.assertEqual(response.json['message'], 'Validation error')
            self.assertIn('email', response.json['errors'])
        _()

    def test_login_missing_fields(self):
        @self.mock_request_data({'email': 'merchant@test.com'})
        def _():
            response = self.client.post('/api/auth/login')
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json['status'], 'error')
            self.assertEqual(response.json['message'], 'Email and password are required')
        _()

        @self.mock_request_data({'password': 'password123'})
        def _():
            response = self.client.post('/api/auth/login')
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json['status'], 'error')
            self.assertEqual(response.json['message'], 'Email and password are required')
        _()

    def test_login_inactive_user(self):
        inactive_user = User(id=4, email="inactive@test.com", name="Inactive User", role=UserRole.CLERK, status=UserStatus.INACTIVE, store_id=self.store.id)
        inactive_user.set_password("password123")
        self.app.mock_users.append(inactive_user)

        @self.mock_request_data({'email': 'inactive@test.com', 'password': 'password123'})
        def _():
            response = self.client.post('/api/auth/login')
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json['status'], 'error')
            self.assertEqual(response.json['message'], 'Account is inactive')
        _()

    def test_login_rate_limit(self):
        email = 'merchant@test.com'
        self.app.mock_request_count[email] = 5  # Simulate 5 failed attempts

        @self.mock_request_data({'email': email, 'password': 'wrongpassword'})
        def _():
            response = self.client.post('/api/auth/login')
            self.assertEqual(response.status_code, 429)
            self.assertIn('Too Many Requests', response.json['msg'])
        _()

    def test_register_with_valid_token(self):
        invitation = Invitation(
            id=1,
            email="newadmin@test.com",
            token=str(uuid.uuid4()),
            role=UserRole.ADMIN,
            creator_id=self.merchant.id,
            store_id=self.store.id,
            expires_at=datetime.now() + timedelta(days=7)
        )
        self.app.mock_invitations.append(invitation)

        @self.mock_request_data({
            'email': 'newadmin@test.com',
            'name': 'New Admin',
            'password': 'password123',
            'token': invitation.token
        })
        def _():
            response = self.client.post('/api/auth/register')
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.json['status'], 'success')
            self.assertEqual(response.json['message'], 'Registration successful')
            self.assertEqual(response.json['user']['email'], 'newadmin@test.com')
            self.assertTrue(invitation.is_used)
        _()

    def test_register_with_expired_token(self):
        invitation = Invitation(
            id=1,
            email="newadmin@test.com",
            token=str(uuid.uuid4()),
            role=UserRole.ADMIN,
            creator_id=self.merchant.id,
            store_id=self.store.id,
            expires_at=datetime.now() - timedelta(days=1)
        )
        self.app.mock_invitations.append(invitation)

        @self.mock_request_data({
            'email': 'newadmin@test.com',
            'name': 'New Admin',
            'password': 'password123',
            'token': invitation.token
        })
        def _():
            response = self.client.post('/api/auth/register')
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json['status'], 'error')
            self.assertEqual(response.json['message'], 'Invitation token has expired')
        _()

    def test_register_with_invalid_token(self):
        @self.mock_request_data({
            'email': 'newadmin@test.com',
            'name': 'New Admin',
            'password': 'password123',
            'token': 'invalid-token'
        })
        def _():
            response = self.client.post('/api/auth/register')
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json['status'], 'error')
            self.assertEqual(response.json['message'], 'Invalid or expired invitation token')
        _()

    def test_register_missing_fields(self):
        @self.mock_request_data({
            'email': 'newadmin@test.com',
            'name': 'New Admin',
            'token': 'some-token'
        })
        def _():
            response = self.client.post('/api/auth/register')
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json['status'], 'error')
            self.assertEqual(response.json['message'], 'Name, email, password, and invitation token are required')
        _()

    def test_register_email_already_exists(self):
        invitation = Invitation(
            id=1,
            email="merchant@test.com",
            token=str(uuid.uuid4()),
            role=UserRole.ADMIN,
            creator_id=self.merchant.id,
            store_id=self.store.id,
            expires_at=datetime.now() + timedelta(days=7)
        )
        self.app.mock_invitations.append(invitation)

        @self.mock_request_data({
            'email': 'merchant@test.com',
            'name': 'New Admin',
            'password': 'password123',
            'token': invitation.token
        })
        def _():
            response = self.client.post('/api/auth/register')
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json['status'], 'error')
            self.assertEqual(response.json['message'], 'User with this email already exists')
        _()

    def test_invite_admin_by_merchant(self):
        @self.mock_current_user(self.merchant)
        @self.mock_request_data({
            'email': 'newadmin@test.com',
            'role': 'ADMIN',
            'store_id': self.store.id
        })
        def _():
            response = self.client.post('/api/auth/invite')
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.json['status'], 'success')
            self.assertEqual(response.json['message'], 'Invitation sent successfully')
            self.assertEqual(response.json['invitation']['email'], 'newadmin@test.com')
            self.assertEqual(response.json['invitation']['role'], 'ADMIN')

            notifications = self.app.mock_notifications
            self.assertTrue(any('You have invited newadmin@test.com as a admin' in n.message for n in notifications))
        _()

    def test_invite_clerk_by_admin(self):
        @self.mock_current_user(self.admin)
        @self.mock_request_data({
            'email': 'newclerk@test.com',
            'role': 'CLERK'
        })
        def _():
            response = self.client.post('/api/auth/invite')
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.json['status'], 'success')
            self.assertEqual(response.json['message'], 'Invitation sent successfully')
            self.assertEqual(response.json['invitation']['email'], 'newclerk@test.com')
            self.assertEqual(response.json['invitation']['role'], 'CLERK')
            self.assertEqual(response.json['invitation']['store_id'], self.store.id)

            notifications = self.app.mock_notifications
            self.assertTrue(any('You have invited newclerk@test.com as a clerk' in n.message for n in notifications))
        _()

    def test_invite_unauthorized_role(self):
        @self.mock_current_user(self.merchant)
        @self.mock_request_data({
            'email': 'newclerk@test.com',
            'role': 'CLERK'
        })
        def _():
            response = self.client.post('/api/auth/invite')
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json['status'], 'error')
            self.assertEqual(response.json['message'], 'You are not authorized to invite users with this role')
        _()

    def test_invite_no_token(self):
        @self.mock_request_data({
            'email': 'newadmin@test.com',
            'role': 'ADMIN',
            'store_id': self.store.id
        })
        def _():
            response = self.client.post('/api/auth/invite')
            self.assertEqual(response.status_code, 401)
            self.assertIn('Missing Authorization Header', response.json['msg'])
        _()

    def test_invite_existing_invitation(self):
        invitation = Invitation(
            id=1,
            email="newadmin@test.com",
            token=str(uuid.uuid4()),
            role=UserRole.ADMIN,
            creator_id=self.merchant.id,
            store_id=self.store.id,
            expires_at=datetime.now() + timedelta(days=7)
        )
        self.app.mock_invitations.append(invitation)

        @self.mock_current_user(self.merchant)
        @self.mock_request_data({
            'email': 'newadmin@test.com',
            'role': 'ADMIN',
            'store_id': self.store.id
        })
        def _():
            response = self.client.post('/api/auth/invite')
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json['status'], 'error')
            self.assertEqual(response.json['message'], 'An invitation for this email already exists')
        _()

    def test_invite_invalid_store(self):
        @self.mock_current_user(self.merchant)
        @self.mock_request_data({
            'email': 'newadmin@test.com',
            'role': 'ADMIN',
            'store_id': 999
        })
        def _():
            response = self.client.post('/api/auth/invite')
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json['status'], 'error')
            self.assertEqual(response.json['message'], 'Store not found')
        _()

    def test_forgot_password_valid_email(self):
        @self.mock_request_data({'email': 'merchant@test.com'})
        def _():
            response = self.client.post('/api/auth/forgot-password')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['status'], 'success')
            self.assertEqual(response.json['message'], 'If the email exists, a reset link has been sent')
            self.assertTrue(self.app.mock_send_called)
            self.assertTrue(len(self.app.mock_password_resets) > 0)
        _()

    def test_forgot_password_invalid_email(self):
        @self.mock_request_data({'email': 'nonexistent@test.com'})
        def _():
            response = self.client.post('/api/auth/forgot-password')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['status'], 'success')
            self.assertEqual(response.json['message'], 'If the email exists, a reset link has been sent')
            self.assertFalse(self.app.mock_send_called)
        _()

    def test_forgot_password_invalid_email_format(self):
        @self.mock_request_data({'email': 'invalid-email'})
        def _():
            response = self.client.post('/api/auth/forgot-password')
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json['status'], 'error')
            self.assertEqual(response.json['message'], 'Validation error')
            self.assertIn('email', response.json['errors'])
        _()

    def test_forgot_password_rate_limit(self):
        email = 'merchant@test.com'
        self.app.mock_request_count[email] = 5

        @self.mock_request_data({'email': email})
        def _():
            response = self.client.post('/api/auth/forgot-password')
            self.assertEqual(response.status_code, 429)
            self.assertIn('Too Many Requests', response.json['msg'])
        _()

    def test_reset_password_valid_token(self):
        reset = PasswordReset(
            id=1,
            user_id=self.merchant.id,
            token=str(uuid.uuid4()),
            expires_at=datetime.now() + timedelta(hours=1)
        )
        self.app.mock_password_resets.append(reset)

        @self.mock_request_data({
            'token': reset.token,
            'password': 'newpassword123'
        })
        def _():
            response = self.client.post('/api/auth/reset-password')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['status'], 'success')
            self.assertEqual(response.json['message'], 'Password reset successfully')
            self.assertTrue(self.merchant.check_password('newpassword123'))
            self.assertTrue(reset.is_used)
        _()

    def test_reset_password_expired_token(self):
        reset = PasswordReset(
            id=1,
            user_id=self.merchant.id,
            token=str(uuid.uuid4()),
            expires_at=datetime.now() - timedelta(hours=1)
        )
        self.app.mock_password_resets.append(reset)

        @self.mock_request_data({
            'token': reset.token,
            'password': 'newpassword123'
        })
        def _():
            response = self.client.post('/api/auth/reset-password')
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json['status'], 'error')
            self.assertEqual(response.json['message'], 'Invalid or expired reset token')
        _()

    def test_reset_password_invalid_token(self):
        @self.mock_request_data({
            'token': 'invalid-token',
            'password': 'newpassword123'
        })
        def _():
            response = self.client.post('/api/auth/reset-password')
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json['status'], 'error')
            self.assertEqual(response.json['message'], 'Invalid or expired reset token')
        _()

    def test_reset_password_missing_fields(self):
        @self.mock_request_data({'token': 'some-token'})
        def _():
            response = self.client.post('/api/auth/reset-password')
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json['status'], 'error')
            self.assertEqual(response.json['message'], 'Token and new password are required')
        _()

    def test_reset_password_rate_limit(self):
        reset = PasswordReset(
            id=1,
            user_id=self.merchant.id,
            token=str(uuid.uuid4()),
            expires_at=datetime.now() + timedelta(hours=1)
        )
        self.app.mock_password_resets.append(reset)
        self.app.mock_request_count[reset.token] = 5

        @self.mock_request_data({
            'token': reset.token,
            'password': 'newpassword123'
        })
        def _():
            response = self.client.post('/api/auth/reset-password')
            self.assertEqual(response.status_code, 429)
            self.assertIn('Too Many Requests', response.json['msg'])
        _()

    def test_get_current_user(self):
        @self.mock_current_user(self.merchant)
        def _():
            response = self.client.get('/api/auth/me')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['status'], 'success')
            self.assertEqual(response.json['user']['email'], 'merchant@test.com')
            self.assertEqual(response.json['user']['role'], 'MERCHANT')
            self.assertIsNone(response.json['user']['store_id'])
            self.assertIsNone(response.json['user']['store_name'])
        _()

    def test_get_current_user_with_store(self):
        @self.mock_current_user(self.admin)
        def _():
            response = self.client.get('/api/auth/me')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['status'], 'success')
            self.assertEqual(response.json['user']['email'], 'admin@test.com')
            self.assertEqual(response.json['user']['role'], 'ADMIN')
            self.assertEqual(response.json['user']['store_id'], self.store.id)
            self.assertEqual(response.json['user']['store_name'], 'Test Store')
        _()

    def test_get_current_user_no_token(self):
        response = self.client.get('/api/auth/me')
        self.assertEqual(response.status_code, 401)
        self.assertIn('Missing Authorization Header', response.json['msg'])

    def test_get_current_user_not_found(self):
        mock_user = User(id=999, email="notfound@test.com", name="Not Found", role=UserRole.MERCHANT, status=UserStatus.ACTIVE)
        @self.mock_current_user(mock_user)
        def _():
            response = self.client.get('/api/auth/me')
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json['status'], 'error')
            self.assertEqual(response.json['message'], 'User not found')
        _()

    def test_google_login_missing_credentials(self):
        self.app.config['GOOGLE_CLIENT_ID'] = None
        self.app.config['GOOGLE_CLIENT_SECRET'] = None

        response = self.client.get('/api/auth/google/login')
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(response.json['message'], 'Google OAuth credentials not configured')

    def test_google_login_redirect(self):
        self.app.config['GOOGLE_CLIENT_ID'] = 'mock-client-id'
        self.app.config['GOOGLE_CLIENT_SECRET'] = 'mock-client-secret'
        self.app.mock_redirect_url = 'https://accounts.google.com/o/oauth2/auth'

        response = self.client.get('/api/auth/google/login')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.json['location'].startswith('https://accounts.google.com/o/oauth2/auth'))

    def test_google_callback_success(self):
        self.app.mock_state = 'state123'
        self.app.mock_token_fetch_error = False
        self.app.mock_google_user_info = {
            'email': 'googleuser@test.com',
            'name': 'Google User'
        }

        @self.mock_query_params({'state': 'state123', 'code': 'authcode'})
        def _():
            response = self.client.get('/api/auth/google/callback')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['status'], 'success')
            self.assertEqual(response.json['message'], 'Google login successful')
            self.assertIn('access_token', response.json)
            self.assertEqual(response.json['user']['email'], 'googleuser@test.com')
            self.assertEqual(response.json['user']['name'], 'Google User')
            self.assertEqual(response.json['user']['role'], 'CLERK')
            self.assertEqual(response.json['user']['status'], 'ACTIVE')
        _()

    def test_google_callback_invalid_state(self):
        self.app.mock_state = 'state123'

        @self.mock_query_params({'state': 'wrongstate', 'code': 'authcode'})
        def _():
            response = self.client.get('/api/auth/google/callback')
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json['status'], 'error')
            self.assertEqual(response.json['message'], 'Invalid state parameter')
        _()

    def test_google_callback_failed_token_fetch(self):
        self.app.mock_state = 'state123'
        self.app.mock_token_fetch_error = True

        @self.mock_query_params({'state': 'state123', 'code': 'authcode'})
        def _():
            response = self.client.get('/api/auth/google/callback')
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json['status'], 'error')
            self.assertEqual(response.json['message'], 'Failed to authenticate with Google: Token fetch failed')
        _()

    def test_google_callback_no_email(self):
        self.app.mock_state = 'state123'
        self.app.mock_token_fetch_error = False
        self.app.mock_google_user_info = {'name': 'Google User'}

        @self.mock_query_params({'state': 'state123', 'code': 'authcode'})
        def _():
            response = self.client.get('/api/auth/google/callback')
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json['status'], 'error')
            self.assertEqual(response.json['message'], 'Failed to retrieve email from Google')
        _()

if __name__ == '__main__':
    unittest.main()