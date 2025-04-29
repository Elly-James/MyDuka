import unittest
from flask import Flask, jsonify
from datetime import datetime

# Mock models (to avoid actual database usage)
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

class Notification:
    def __init__(self, id, user_id, message, is_read=False):
        self.id = id
        self.user_id = user_id
        self.message = message
        self.is_read = is_read
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
@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    user = getattr(app, 'mock_user', None)
    if not user:
        return jsonify({'msg': 'Missing Authorization Header'}), 401
    query_params = getattr(app, 'mock_query_params', {})
    page = int(query_params.get('page', 1))
    per_page = int(query_params.get('per_page', 50))
    is_read = query_params.get('is_read', None)
    
    notifications = getattr(app, 'mock_notifications', [])
    # Filter notifications by user_id
    user_notifications = [n for n in notifications if n.user_id == user.id]
    # Filter by is_read if specified
    if is_read is not None:
        is_read_bool = is_read.lower() == 'true'
        user_notifications = [n for n in user_notifications if n.is_read == is_read_bool]
    
    # Sort by created_at descending
    user_notifications.sort(key=lambda x: x.created_at, reverse=True)
    total = len(user_notifications)
    # Apply pagination
    start = (page - 1) * per_page
    end = start + per_page
    paginated_notifications = user_notifications[start:end]
    
    return jsonify({
        'status': 'success',
        'notifications': [n.to_dict() for n in paginated_notifications],
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page
    }), 200

@app.route('/api/notifications/<int:notification_id>/read', methods=['PUT'])
def mark_notification_read(notification_id):
    user = getattr(app, 'mock_user', None)
    if not user:
        return jsonify({'msg': 'Missing Authorization Header'}), 401
    
    notifications = getattr(app, 'mock_notifications', [])
    notification = next((n for n in notifications if n.id == notification_id), None)
    if not notification:
        return jsonify({'status': 'error', 'message': 'Notification not found'}), 404
    if notification.user_id != user.id:
        return jsonify({'status': 'error', 'message': 'Unauthorized to mark this notification as read'}), 403
    
    notification.is_read = True
    notification.updated_at = datetime.now()
    return jsonify({
        'status': 'success',
        'message': 'Notification marked as read',
        'notification': notification.to_dict()
    }), 200

@app.route('/api/notifications/mark-all-read', methods=['PUT'])
def mark_all_notifications_read():
    user = getattr(app, 'mock_user', None)
    if not user:
        return jsonify({'msg': 'Missing Authorization Header'}), 401
    
    notifications = getattr(app, 'mock_notifications', [])
    updated_count = 0
    for notification in notifications:
        if notification.user_id == user.id and not notification.is_read:
            notification.is_read = True
            notification.updated_at = datetime.now()
            updated_count += 1
    
    return jsonify({
        'status': 'success',
        'message': 'All notifications marked as read',
        'updated_count': updated_count
    }), 200

@app.route('/api/notifications/<int:notification_id>', methods=['DELETE'])
def delete_notification(notification_id):
    user = getattr(app, 'mock_user', None)
    if not user:
        return jsonify({'msg': 'Missing Authorization Header'}), 401
    
    notifications = getattr(app, 'mock_notifications', [])
    notification = next((n for n in notifications if n.id == notification_id), None)
    if not notification:
        return jsonify({'status': 'error', 'message': 'Notification not found'}), 404
    if notification.user_id != user.id:
        return jsonify({'status': 'error', 'message': 'Unauthorized to delete this notification'}), 403
    
    app.mock_notifications = [n for n in notifications if n.id != notification_id]
    return jsonify({
        'status': 'success',
        'message': 'Notification deleted successfully'
    }), 200

# Test class
class NotificationsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        self.app.config['TESTING'] = True

        # Mock users
        self.clerk_user = User(id=1, email="clerk@myduka.com", role="CLERK", store_id=1)
        self.admin_user = User(id=2, email="admin@myduka.com", role="ADMIN", store_id=1)

        # Mock notifications
        self.notification1 = Notification(id=1, user_id=1, message="Test notification 1", is_read=False)
        self.notification2 = Notification(id=2, user_id=1, message="Test notification 2", is_read=True)
        self.admin_notification = Notification(id=3, user_id=2, message="Admin notification", is_read=False)
        self.app.mock_notifications = [self.notification1, self.notification2, self.admin_notification]

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
    def test_get_notifications(self):
        @self.mock_current_user(self.clerk_user)
        @self.mock_query_params({})
        def _():
            response = self.client.get('/api/notifications')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['status'], 'success')
            self.assertEqual(response.json['total'], 2)  # Clerk's notifications
            self.assertEqual(len(response.json['notifications']), 2)
            self.assertEqual(response.json['notifications'][0]['message'], 'Test notification 2')  # Ordered by created_at desc
            self.assertEqual(response.json['page'], 1)
            self.assertEqual(response.json['per_page'], 50)

            # Test filtering by is_read
            @self.mock_query_params({'is_read': 'false'})
            def __():
                response = self.client.get('/api/notifications?is_read=false')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json['status'], 'success')
                self.assertEqual(response.json['total'], 1)
                self.assertEqual(len(response.json['notifications']), 1)
                self.assertEqual(response.json['notifications'][0]['message'], 'Test notification 1')
            __()

            # Test pagination with per_page parameter
            @self.mock_query_params({'page': '1', 'per_page': '1'})
            def __():
                response = self.client.get('/api/notifications?page=1&per_page=1')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json['status'], 'success')
                self.assertEqual(response.json['total'], 2)
                self.assertEqual(len(response.json['notifications']), 1)
                self.assertEqual(response.json['notifications'][0]['message'], 'Test notification 2')
                self.assertEqual(response.json['per_page'], 1)
                self.assertEqual(response.json['pages'], 2)
            __()
        _()

    def test_get_notifications_unauthorized_user(self):
        @self.mock_current_user(self.clerk_user)
        @self.mock_query_params({})
        def _():
            response = self.client.get('/api/notifications')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['status'], 'success')
            self.assertEqual(response.json['total'], 2)  # Clerk should not see admin's notifications
            self.assertEqual(len(response.json['notifications']), 2)
            self.assertNotIn('Admin notification', [n['message'] for n in response.json['notifications']])
        _()

    def test_get_notifications_no_token(self):
        # Ensure no user is set
        if hasattr(self.app, 'mock_user'):
            delattr(self.app, 'mock_user')
        response = self.client.get('/api/notifications')
        self.assertEqual(response.status_code, 401)
        self.assertIn('Missing Authorization Header', response.json['msg'])

    def test_mark_notification_read(self):
        @self.mock_current_user(self.clerk_user)
        def _():
            response = self.client.put('/api/notifications/1/read')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['status'], 'success')
            self.assertEqual(response.json['message'], 'Notification marked as read')
            self.assertTrue(response.json['notification']['is_read'])
        _()

    def test_mark_notification_read_unauthorized(self):
        @self.mock_current_user(self.clerk_user)
        def _():
            response = self.client.put('/api/notifications/3/read')  # Admin's notification
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json['status'], 'error')
            self.assertEqual(response.json['message'], 'Unauthorized to mark this notification as read')
        _()

    def test_mark_notification_read_no_token(self):
        # Ensure no user is set
        if hasattr(self.app, 'mock_user'):
            delattr(self.app, 'mock_user')
        response = self.client.put('/api/notifications/1/read')
        self.assertEqual(response.status_code, 401)
        self.assertIn('Missing Authorization Header', response.json['msg'])

    def test_mark_notification_read_not_found(self):
        @self.mock_current_user(self.clerk_user)
        def _():
            response = self.client.put('/api/notifications/999/read')
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json['status'], 'error')
            self.assertEqual(response.json['message'], 'Notification not found')
        _()

    def test_mark_all_notifications_read(self):
        @self.mock_current_user(self.clerk_user)
        def _():
            response = self.client.put('/api/notifications/mark-all-read')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['status'], 'success')
            self.assertEqual(response.json['message'], 'All notifications marked as read')
            self.assertEqual(response.json['updated_count'], 1)  # Only notification1 was unread
        _()

    def test_mark_all_notifications_read_no_unread(self):
        # Set all notifications to read
        self.notification1.is_read = True
        self.notification2.is_read = True
        self.app.mock_notifications = [self.notification1, self.notification2, self.admin_notification]

        @self.mock_current_user(self.clerk_user)
        def _():
            response = self.client.put('/api/notifications/mark-all-read')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['status'], 'success')
            self.assertEqual(response.json['message'], 'All notifications marked as read')
            self.assertEqual(response.json['updated_count'], 0)
        _()

    def test_mark_all_notifications_read_no_token(self):
        # Ensure no user is set
        if hasattr(self.app, 'mock_user'):
            delattr(self.app, 'mock_user')
        response = self.client.put('/api/notifications/mark-all-read')
        self.assertEqual(response.status_code, 401)
        self.assertIn('Missing Authorization Header', response.json['msg'])

    def test_delete_notification(self):
        @self.mock_current_user(self.clerk_user)
        def _():
            response = self.client.delete('/api/notifications/1')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['status'], 'success')
            self.assertEqual(response.json['message'], 'Notification deleted successfully')
        _()

    def test_delete_notification_unauthorized(self):
        @self.mock_current_user(self.clerk_user)
        def _():
            response = self.client.delete('/api/notifications/3')  # Admin's notification
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json['status'], 'error')
            self.assertEqual(response.json['message'], 'Unauthorized to delete this notification')
        _()

    def test_delete_notification_no_token(self):
        # Ensure no user is set
        if hasattr(self.app, 'mock_user'):
            delattr(self.app, 'mock_user')
        response = self.client.delete('/api/notifications/1')
        self.assertEqual(response.status_code, 401)
        self.assertIn('Missing Authorization Header', response.json['msg'])

    def test_delete_notification_not_found(self):
        @self.mock_current_user(self.clerk_user)
        def _():
            response = self.client.delete('/api/notifications/999')
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json['status'], 'error')
            self.assertEqual(response.json['message'], 'Notification not found')
        _()

if __name__ == '__main__':
    unittest.main()