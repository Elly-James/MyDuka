from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging

from extensions import db, socketio  # Added socketio import
from models import User, UserRole, UserStatus, Store, Notification
from schemas import UserSchema, NotificationSchema, UserStatusUpdateSchema, UserStatusInputSchema

users_bp = Blueprint('users', __name__, url_prefix='/api/users')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@users_bp.route('', methods=['GET'])
@jwt_required()
def get_users():
    """
    Get users list with filters.

    Query Parameters:
        - role (str, optional): Filter by role (e.g., 'ADMIN', 'CLERK')
        - store_id (int, optional): Filter by store ID (for Merchants)
        - status (str, optional): Filter by status (e.g., 'ACTIVE', 'INACTIVE')
        - page (int, optional): Page number (default 1)
        - per_page (int, optional): Number of users per page (default 50)

    Responses:
        - 200: List of users
        - 400: Invalid role or status
        - 403: Unauthorized to view users
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
        
        if current_user.role == UserRole.CLERK:
            return jsonify({
                'status': 'error',
                'message': 'Unauthorized to view users'
            }), 403
        
        role = request.args.get('role')
        store_id = request.args.get('store_id', type=int)
        status = request.args.get('status')
        page = request.args.get('page', default=1, type=int)
        per_page = request.args.get('per_page', default=50, type=int)
        
        query = User.query
        
        if role:
            try:
                query = query.filter_by(role=UserRole[role.upper()])
            except KeyError:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid role'
                }), 400
        
        if status:
            try:
                query = query.filter_by(status=UserStatus[status.upper()])
            except KeyError:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid status'
                }), 400
        
        if current_user.role == UserRole.ADMIN:
            query = query.filter_by(store_id=current_user.store_id)
        elif store_id and current_user.role == UserRole.MERCHANT:
            query = query.filter_by(store_id=store_id)
        
        # Apply pagination
        paginated_users = query.paginate(page=page, per_page=per_page, error_out=False)
        users = paginated_users.items
        
        # Use UserSchema to serialize user data
        user_schema = UserSchema()
        result = []
        for user in users:
            store = db.session.get(Store, user.store_id) if user.store_id else None
            user_data = user_schema.dump(user)
            # Add additional fields not covered by UserSchema
            user_data.update({
                'id': user.id,
                'store_id': user.store_id,
                'store_name': store.name if store else None,
                'created_at': user.created_at.isoformat(),
                'updated_at': user.updated_at.isoformat()
            })
            result.append(user_data)
        
        logger.info(f"Users list retrieved by user ID: {current_user_id}")
        return jsonify({
            'status': 'success',
            'users': result,
            'total': paginated_users.total,
            'page': page,
            'per_page': per_page,
            'pages': paginated_users.pages
        }), 200
    except Exception as e:
        logger.error(f"Error in get_users for user ID {current_user_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

@users_bp.route('/<int:user_id>/status', methods=['PUT'])
@jwt_required()
def update_user_status(user_id):
    """
    Update user status (activate/deactivate).

    Request Body:
        - status (str): New status ('ACTIVE' or 'INACTIVE')

    Responses:
        - 200: User status updated successfully
        - 400: Missing or invalid status
        - 403: Unauthorized to update user status
        - 404: Current user or target user not found
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
        
        if current_user.role == UserRole.CLERK:
            return jsonify({
                'status': 'error',
                'message': 'Unauthorized to update user status'
            }), 403
        
        target_user = db.session.get(User, user_id)
        if not target_user:
            return jsonify({
                'status': 'error',
                'message': 'Target user not found'
            }), 404
        
        if current_user.role == UserRole.ADMIN:
            if target_user.role != UserRole.CLERK or target_user.store_id != current_user.store_id:
                return jsonify({
                    'status': 'error',
                    'message': 'You can only manage clerks in your store'
                }), 403
        elif current_user.role == UserRole.MERCHANT:
            if target_user.role != UserRole.ADMIN:
                return jsonify({
                    'status': 'error',
                    'message': 'You can only manage admins'
                }), 403
        
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Request body is required'
            }), 400
        
        # Validate input using UserStatusInputSchema
        input_schema = UserStatusInputSchema()
        errors = input_schema.validate(data)
        if errors:
            return jsonify({
                'status': 'error',
                'message': 'Validation error',
                'errors': errors
            }), 400
        
        new_status = UserStatus[data['status'].upper()]
        
        with db.session.begin_nested():
            target_user.status = new_status
            
            # Notify the target user
            notification_data = {
                'user_id': target_user.id,
                'message': f"Your account status has been updated to {new_status.name.lower()} by {current_user.name}.",
                'is_read': False
            }
            notification = Notification(**notification_data)
            db.session.add(notification)
            db.session.flush()
            
            # Serialize the notification
            notification_schema = NotificationSchema()
            serialized_notification = notification_schema.dump(notification)
            
            # Emit WebSocket event for the notification
            socketio.emit('new_notification', {
                'id': notification.id,
                'message': notification.message,
                'created_at': notification.created_at.isoformat()
            }, room=f'user_{target_user.id}')
        
        db.session.commit()
        
        # Serialize the updated user status
        user_status_update_schema = UserStatusUpdateSchema()
        user_data = user_status_update_schema.dump({
            'id': target_user.id,
            'status': target_user.status.name
        })
        
        logger.info(f"User ID {user_id} status updated to {new_status.name} by user ID: {current_user_id}")
        return jsonify({
            'status': 'success',
            'message': f'User status updated to {new_status.name.lower()} successfully',
            'user': user_data,
            'notification': serialized_notification
        }), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in update_user_status for user ID {current_user_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

@users_bp.route('/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    """
    Delete a user.

    Responses:
        - 200: User deleted successfully
        - 403: Unauthorized to delete users
        - 404: Current user or target user not found
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
        
        if current_user.role == UserRole.CLERK:
            return jsonify({
                'status': 'error',
                'message': 'Unauthorized to delete users'
            }), 403
        
        target_user = db.session.get(User, user_id)
        if not target_user:
            return jsonify({
                'status': 'error',
                'message': 'Target user not found'
            }), 404
        
        if current_user.role == UserRole.ADMIN:
            if target_user.role != UserRole.CLERK or target_user.store_id != current_user.store_id:
                return jsonify({
                    'status': 'error',
                    'message': 'You can only delete clerks in your store'
                }), 403
        elif current_user.role == UserRole.MERCHANT:
            if target_user.role != UserRole.ADMIN:
                return jsonify({
                    'status': 'error',
                    'message': 'You can only delete admins'
                }), 403
        
        # Determine who to notify (e.g., Merchant if an Admin deletes a Clerk, or Admins if a Merchant deletes an Admin)
        notify_user_ids = []
        if current_user.role == UserRole.ADMIN:
            # Notify the Merchant of the store
            merchant = User.query.filter_by(role=UserRole.MERCHANT, store_id=current_user.store_id).first()
            if merchant:
                notify_user_ids.append(merchant.id)
        elif current_user.role == UserRole.MERCHANT:
            # Notify all Admins of the store
            admins = User.query.filter_by(role=UserRole.ADMIN, store_id=target_user.store_id).all()
            notify_user_ids.extend([admin.id for admin in admins])
        
        with db.session.begin_nested():
            db.session.delete(target_user)
            db.session.flush()
            
            # Emit WebSocket events to notify relevant users
            for notify_user_id in notify_user_ids:
                socketio.emit('user_deleted', {
                    'user_id': user_id,
                    'message': f"User {target_user.name} has been deleted by {current_user.name}."
                }, room=f'user_{notify_user_id}')
        
        db.session.commit()
        
        logger.info(f"User ID {user_id} deleted by user ID: {current_user_id}")
        return jsonify({
            'status': 'success',
            'message': 'User deleted successfully'
        }), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in delete_user for user ID {current_user_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500