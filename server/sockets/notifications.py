from flask_socketio import emit, join_room, leave_room
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import socketio

@socketio.on('connect')
@jwt_required()
def handle_connect():
    """Authenticate and set up user's notification room"""
    try:
        user_id = get_jwt_identity()['id']
        join_room(f'user_{user_id}')
        emit('connection_success', {
            'message': 'Connected to notifications',
            'user_id': user_id
        })
    except Exception as e:
        emit('connection_error', {
            'message': 'Authentication failed',
            'error': str(e)
        })

@socketio.on('disconnect')
def handle_disconnect():
    """Clean up on disconnect"""
    try:
        user_id = get_jwt_identity()['id']
        leave_room(f'user_{user_id}')
    except:
        pass  # Handle cases where JWT might not be available

@socketio.on('subscribe_notifications')
@jwt_required()
def handle_subscribe(data):
    """Send initial unread notifications"""
    from models import Notification
    from schemas import NotificationSchema
    
    user_id = get_jwt_identity()['id']
    unread = Notification.query.filter_by(
        user_id=user_id,
        is_read=False
    ).order_by(Notification.created_at.desc()).limit(50).all()
    
    schema = NotificationSchema(many=True)
    emit('initial_notifications', {
        'notifications': schema.dump(unread),
        'count': len(unread)
    })