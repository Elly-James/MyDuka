import os
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
import logging

from extensions import db, socketio
from models import Notification, User, NotificationType
from schemas import NotificationSchema

notifications_bp = Blueprint('notifications', __name__, url_prefix='/api/notifications')

# Configure logging
logging.basicConfig(level=logging.ERROR if os.getenv('FLASK_ENV') == 'production' else logging.INFO)
logger = logging.getLogger(__name__)

notification_schema = NotificationSchema(many=True)
single_notification_schema = NotificationSchema()

@notifications_bp.route('', methods=['GET'])
@jwt_required()
def get_notifications():
    """
    Retrieve notifications for the current user.
    Query Parameters:
        - is_read (bool, optional): Filter by read status (true/false)
        - page (int, optional): Page number (default 1)
        - per_page (int, optional): Number of notifications per page (default 10)
    Responses:
        - 200: List of notifications with pagination
        - 403: Unauthorized (non-merchant user)
        - 404: User not found
        - 500: Internal server error
    """
    try:
        identity = get_jwt_identity()
        current_user_id = identity['id']
        current_user_role = identity['role']
        logger.info(f"Fetching notifications for user ID: {current_user_id}, role: {current_user_role}")

        if current_user_role != 'MERCHANT':
            logger.warning(f"Unauthorized access attempt by user ID: {current_user_id}")
            return jsonify({'status': 'error', 'message': 'Merchant role required'}), 403

        current_user = db.session.get(User, current_user_id)
        if not current_user:
            logger.error(f"User not found: {current_user_id}")
            return jsonify({'status': 'error', 'message': 'User not found'}), 404

        is_read = request.args.get('is_read', type=lambda v: v.lower() == 'true' if v is not None else None)
        page = request.args.get('page', default=1, type=int)
        per_page = request.args.get('per_page', default=10, type=int)

        query = db.session.query(Notification).filter_by(user_id=current_user_id)

        if is_read is not None:
            query = query.filter_by(is_read=is_read)

        # Optimize query with limit and order by recent
        paginated_notifications = query.order_by(Notification.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        notifications = paginated_notifications.items

        # Serialize notifications
        result = notification_schema.dump(notifications)

        logger.info(f"Retrieved {len(notifications)} notifications for user ID: {current_user_id}, page: {page}")
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
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@notifications_bp.route('/<int:id>/read', methods=['PUT'])
@jwt_required()
def mark_notification_read(id):
    """
    Mark a specific notification as read.
    Responses:
        - 200: Notification marked as read
        - 403: Unauthorized to mark this notification
        - 404: Notification or user not found
        - 500: Internal server error
    """
    try:
        identity = get_jwt_identity()
        current_user_id = identity['id']
        current_user_role = identity['role']
        logger.info(f"Marking notification ID {id} as read for user ID: {current_user_id}, role: {current_user_role}")

        if current_user_role != 'MERCHANT':
            logger.warning(f"Unauthorized access attempt by user ID: {current_user_id}")
            return jsonify({'status': 'error', 'message': 'Merchant role required'}), 403

        current_user = db.session.get(User, current_user_id)
        if not current_user:
            logger.error(f"User not found: {current_user_id}")
            return jsonify({'status': 'error', 'message': 'User not found'}), 404

        notification = db.session.get(Notification, id)
        if not notification:
            logger.error(f"Notification not found: {id} for user ID: {current_user_id}")
            return jsonify({'status': 'error', 'message': 'Notification not found'}), 404

        if notification.user_id != current_user_id:
            logger.warning(f"Unauthorized attempt to mark notification {id} by user ID: {current_user_id}")
            return jsonify({'status': 'error', 'message': 'Unauthorized to mark this notification as read'}), 403

        try:
            with db.session.begin_nested():
                notification.is_read = True
                notification.updated_at = datetime.utcnow()
                db.session.flush()

                # Serialize updated notification
                updated_notification = single_notification_schema.dump(notification)

                # Emit WebSocket event
                socketio.emit('notification_updated', {
                    'id': notification.id,
                    'is_read': notification.is_read,
                    'message': notification.message,
                    'type': notification.type.value,
                    'updated_at': notification.updated_at.isoformat()
                }, namespace='/', room=f'user_{current_user_id}')

            db.session.commit()
            logger.info(f"Notification ID {id} marked as read by user ID: {current_user_id}, type: {notification.type.value}")
            return jsonify({
                'status': 'success',
                'message': 'Notification marked as read',
                'notification': updated_notification
            }), 200

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error marking notification ID {id} as read for user ID {current_user_id}: {str(e)}")
            return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

    except Exception as e:
        logger.error(f"Error in mark_notification_read for notification ID {id} by user ID {current_user_id}: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@notifications_bp.route('/mark-all-read', methods=['PUT'])
@jwt_required()
def mark_all_notifications_read():
    """
    Mark all notifications for the current user as read.
    Responses:
        - 200: All notifications marked as read
        - 403: Unauthorized (non-merchant user)
        - 404: User not found
        - 500: Internal server error
    """
    try:
        identity = get_jwt_identity()
        current_user_id = identity['id']
        current_user_role = identity['role']
        logger.info(f"Marking all notifications as read for user ID: {current_user_id}, role: {current_user_role}")

        if current_user_role != 'MERCHANT':
            logger.warning(f"Unauthorized access attempt by user ID: {current_user_id}")
            return jsonify({'status': 'error', 'message': 'Merchant role required'}), 403

        current_user = db.session.get(User, current_user_id)
        if not current_user:
            logger.error(f"User not found: {current_user_id}")
            return jsonify({'status': 'error', 'message': 'User not found'}), 404

        try:
            with db.session.begin_nested():
                notifications = db.session.query(Notification).filter_by(
                    user_id=current_user_id, is_read=False
                ).all()
                updated_count = 0
                for notification in notifications:
                    notification.is_read = True
                    notification.updated_at = datetime.utcnow()
                    updated_count += 1
                db.session.flush()

                # Emit WebSocket event
                socketio.emit('notifications_updated', {
                    'user_id': current_user_id,
                    'message': 'All notifications marked as read',
                    'updated_count': updated_count,
                    'updated_at': datetime.utcnow().isoformat(),
                    'type': 'bulk_update'
                }, namespace='/', room=f'user_{current_user_id}')

            db.session.commit()
            logger.info(f"Marked {updated_count} notifications as read for user ID: {current_user_id}")
            return jsonify({
                'status': 'success',
                'message': 'All notifications marked as read',
                'updated_count': updated_count
            }), 200

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error marking all notifications as read for user ID {current_user_id}: {str(e)}")
            return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

    except Exception as e:
        logger.error(f"Error in mark_all_notifications_read for user ID {current_user_id}: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@notifications_bp.route('/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_notification(id):
    """
    Delete a specific notification.
    Responses:
        - 200: Notification deleted successfully
        - 403: Unauthorized to delete this notification
        - 404: Notification or user not found
        - 500: Internal server error
    """
    try:
        identity = get_jwt_identity()
        current_user_id = identity['id']
        current_user_role = identity['role']
        logger.info(f"Deleting notification ID {id} for user ID: {current_user_id}, role: {current_user_role}")

        if current_user_role != 'MERCHANT':
            logger.warning(f"Unauthorized access attempt by user ID: {current_user_id}")
            return jsonify({'status': 'error', 'message': 'Merchant role required'}), 403

        current_user = db.session.get(User, current_user_id)
        if not current_user:
            logger.error(f"User not found: {current_user_id}")
            return jsonify({'status': 'error', 'message': 'User not found'}), 404

        notification = db.session.get(Notification, id)
        if not notification:
            logger.error(f"Notification not found: {id} for user ID: {current_user_id}")
            return jsonify({'status': 'error', 'message': 'Notification not found'}), 404

        if notification.user_id != current_user_id:
            logger.warning(f"Unauthorized attempt to delete notification {id} by user ID: {current_user_id}")
            return jsonify({'status': 'error', 'message': 'Unauthorized to delete this notification'}), 403

        try:
            with db.session.begin_nested():
                notification_type = notification.type.value
                db.session.delete(notification)
                db.session.flush()

                # Emit WebSocket event
                socketio.emit('notification_deleted', {
                    'id': id,
                    'message': 'Notification deleted',
                    'type': notification_type,
                    'deleted_at': datetime.utcnow().isoformat()
                }, namespace='/', room=f'user_{current_user_id}')

            db.session.commit()
            logger.info(f"Notification ID {id} deleted by user ID: {current_user_id}, type: {notification_type}")
            return jsonify({
                'status': 'success',
                'message': 'Notification deleted successfully'
            }), 200

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting notification ID {id} for user ID {current_user_id}: {str(e)}")
            return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

    except Exception as e:
        logger.error(f"Error in delete_notification for notification ID {id} by user ID {current_user_id}: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500