from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging

from extensions import db, socketio  # Added socketio import
from models import Notification, User
from schemas import NotificationSchema

notifications_bp = Blueprint('notifications', __name__, url_prefix='/api/notifications')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100 per day", "50 per hour"]
)

@notifications_bp.route('', methods=['GET'])
@jwt_required()
def get_notifications():
    """
    Retrieve notifications for the current user.

    Query Parameters:
        - is_read (bool, optional): Filter by read status (true/false)
        - page (int, optional): Page number (default 1)
        - per_page (int, optional): Number of notifications per page (default 50)

    Responses:
        - 200: List of notifications
        - 404: User not found
        - 500: Internal server error
    """
    try:
        current_user_id = get_jwt_identity()['id']
        current_user = db.session.get(User, current_user_id)
        if not current_user:
            return jsonify({
                'status': 'error',
                'message': 'User not found'
            }), 404

        is_read = request.args.get('is_read', type=lambda v: v.lower() == 'true' if v is not None else None)
        page = request.args.get('page', default=1, type=int)
        per_page = request.args.get('per_page', default=50, type=int)

        query = Notification.query.filter_by(user_id=current_user_id)

        if is_read is not None:
            query = query.filter_by(is_read=is_read)

        # Apply pagination
        paginated_notifications = query.order_by(Notification.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        notifications = paginated_notifications.items

        # Use NotificationSchema to serialize the notifications
        notification_schema = NotificationSchema(many=True)
        result = notification_schema.dump(notifications)

        logger.info(f"Notifications retrieved for user ID: {current_user_id} from IP: {get_remote_address()}")
        return jsonify({
            'status': 'success',
            'notifications': result,
            'total': paginated_notifications.total,
            'page': page,
            'per_page': per_page,
            'pages': paginated_notifications.pages
        }), 200

    except Exception as e:
        logger.error(f"Error in get_notifications for user ID {current_user_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

@notifications_bp.route('/<int:id>/read', methods=['PUT'])
@jwt_required()
@limiter.limit("10 per minute")
def mark_notification_read(id):
    """
    Mark a specific notification as read.

    Responses:
        - 200: Notification marked as read
        - 404: Notification or user not found
        - 403: Unauthorized to mark this notification
        - 500: Internal server error
    """
    try:
        current_user_id = get_jwt_identity()['id']
        current_user = db.session.get(User, current_user_id)
        if not current_user:
            return jsonify({
                'status': 'error',
                'message': 'User not found'
            }), 404

        notification = db.session.get(Notification, id)
        if not notification:
            return jsonify({
                'status': 'error',
                'message': 'Notification not found'
            }), 404

        if notification.user_id != current_user_id:
            return jsonify({
                'status': 'error',
                'message': 'Unauthorized to mark this notification as read'
            }), 403

        with db.session.begin_nested():
            notification.is_read = True
            db.session.flush()

            # Emit WebSocket event for the updated notification
            socketio.emit('notification_updated', {
                'id': notification.id,
                'is_read': notification.is_read,
                'updated_at': notification.updated_at.isoformat()
            }, room=f'user_{current_user_id}')

        db.session.commit()

        # Use NotificationSchema to serialize the updated notification
        notification_schema = NotificationSchema()
        updated_notification = notification_schema.dump(notification)

        logger.info(f"Notification ID {id} marked as read by user ID: {current_user_id} from IP: {get_remote_address()}")
        return jsonify({
            'status': 'success',
            'message': 'Notification marked as read',
            'notification': updated_notification
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in mark_notification_read for notification ID {id} by user ID {current_user_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

@notifications_bp.route('/mark-all-read', methods=['PUT'])
@jwt_required()
@limiter.limit("5 per minute")
def mark_all_notifications_read():
    """
    Mark all notifications for the current user as read.

    Responses:
        - 200: All notifications marked as read
        - 404: User not found
        - 500: Internal server error
    """
    try:
        current_user_id = get_jwt_identity()['id']
        current_user = db.session.get(User, current_user_id)
        if not current_user:
            return jsonify({
                'status': 'error',
                'message': 'User not found'
            }), 404

        with db.session.begin_nested():
            notifications = Notification.query.filter_by(user_id=current_user_id, is_read=False).all()
            for notification in notifications:
                notification.is_read = True
            db.session.flush()

            # Emit WebSocket event for all updated notifications
            socketio.emit('notifications_updated', {
                'user_id': current_user_id,
                'message': 'All notifications marked as read',
                'updated_count': len(notifications)
            }, room=f'user_{current_user_id}')

        db.session.commit()

        logger.info(f"All notifications marked as read for user ID: {current_user_id} from IP: {get_remote_address()}")
        return jsonify({
            'status': 'success',
            'message': 'All notifications marked as read',
            'updated_count': len(notifications)
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in mark_all_notifications_read for user ID {current_user_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

@notifications_bp.route('/<int:id>', methods=['DELETE'])
@jwt_required()
@limiter.limit("10 per minute")
def delete_notification(id):
    """
    Delete a specific notification.

    Responses:
        - 200: Notification deleted successfully
        - 404: Notification or user not found
        - 403: Unauthorized to delete this notification
        - 500: Internal server error
    """
    try:
        current_user_id = get_jwt_identity()['id']
        current_user = db.session.get(User, current_user_id)
        if not current_user:
            return jsonify({
                'status': 'error',
                'message': 'User not found'
            }), 404

        notification = db.session.get(Notification, id)
        if not notification:
            return jsonify({
                'status': 'error',
                'message': 'Notification not found'
            }), 404

        if notification.user_id != current_user_id:
            return jsonify({
                'status': 'error',
                'message': 'Unauthorized to delete this notification'
            }), 403

        with db.session.begin_nested():
            db.session.delete(notification)
            db.session.flush()

            # Emit WebSocket event for the deleted notification
            socketio.emit('notification_deleted', {
                'id': id,
                'message': 'Notification deleted'
            }, room=f'user_{current_user_id}')

        db.session.commit()

        logger.info(f"Notification ID {id} deleted by user ID: {current_user_id} from IP: {get_remote_address()}")
        return jsonify({
            'status': 'success',
            'message': 'Notification deleted successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in delete_notification for notification ID {id} by user ID {current_user_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500