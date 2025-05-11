from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import selectinload
from extensions import db, socketio
from models import User, UserRole, UserStatus, Store, Notification, NotificationType, user_store
from schemas import UserSchema
from sqlalchemy import or_
from marshmallow import ValidationError
import logging
from functools import wraps

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Role-based authorization decorator
def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            identity = get_jwt_identity()
            current_user_role = identity.get('role')
            if not current_user_role or UserRole[current_user_role] not in allowed_roles:
                logger.warning(f"Unauthorized access attempt by user ID: {identity.get('id')} with role: {current_user_role}")
                return jsonify({'status': 'error', 'message': 'Insufficient permissions'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

users_bp = Blueprint('users', __name__, url_prefix='/api/users')

user_schema = UserSchema()
users_schema = UserSchema(many=True)

@users_bp.route('', methods=['GET'])
@jwt_required()
@role_required([UserRole.MERCHANT])
def get_users():
    """
    Get users list with filters.
    Query Parameters:
        - role (str, optional): Filter by role (e.g., 'ADMIN')
        - search (str, optional): Search by name, email, or store name
        - page (int, optional): Page number (default 1)
        - per_page (int, optional): Number of users per page (default 10)
    Responses:
        - 200: List of users with pagination
        - 403: Unauthorized (non-merchant user)
        - 404: Current user not found
        - 500: Internal server error
    """
    try:
        identity = get_jwt_identity()
        current_user_id = identity['id']
        logger.debug(f"Fetching users for user ID: {current_user_id}")

        role = request.args.get('role', '').strip().upper()
        search = request.args.get('search', '').strip()
        page = max(1, request.args.get('page', 1, type=int))
        per_page = max(1, request.args.get('per_page', 10, type=int))

        query = db.session.query(User).options(selectinload(User.stores))
        if role:
            try:
                query = query.filter(User.role == UserRole[role])
            except KeyError:
                logger.error(f"Invalid role parameter: {role}")
                return jsonify({'status': 'error', 'message': 'Invalid role'}), 400

        if search:
            search_term = f'%{search.lower()}%'
            query = query.join(user_store, User.id == user_store.c.user_id, isouter=True) \
                         .join(Store, user_store.c.store_id == Store.id, isouter=True) \
                         .filter(or_(
                             User.name.ilike(search_term),
                             User.email.ilike(search_term),
                             Store.name.ilike(search_term)
                         ))

        total = query.count()
        pages = (total + per_page - 1) // per_page
        users = query.order_by(User.name.asc()).offset((page - 1) * per_page).limit(per_page).all()
        result = users_schema.dump(users)

        logger.info(f"Retrieved {len(result)} users for user ID: {current_user_id}")
        return jsonify({
            'status': 'success',
            'users': result,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': pages
        }), 200

    except SQLAlchemyError as e:
        logger.error(f"Database error fetching users for user ID {current_user_id}: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Database error'}), 500
    except Exception as e:
        logger.error(f"Error fetching users for user ID {current_user_id}: {type(e).__name__} - {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@users_bp.route('/admins', methods=['GET'])
@jwt_required()
@role_required([UserRole.MERCHANT])
def get_admins():
    """
    Get all admins with associated stores.
    Query Parameters:
        - search (str, optional): Search by name, email, or store name
        - store_id (int, optional): Filter by store ID
        - page (int, optional): Page number (default 1)
        - per_page (int, optional): Admins per page (default 10)
    Responses:
        - 200: List of admins with pagination
        - 403: Unauthorized (non-merchant user or store access)
        - 404: Current user not found
        - 500: Internal server error
    """
    try:
        identity = get_jwt_identity()
        current_user_id = identity['id']
        logger.debug(f"Fetching admins for user ID: {current_user_id}")

        search = request.args.get('search', '').strip()
        store_id = request.args.get('store_id', None, type=int)
        page = max(1, request.args.get('page', 1, type=int))
        per_page = max(1, request.args.get('per_page', 10, type=int))

        query = db.session.query(User).filter(
            User.role == UserRole.ADMIN,
            User.id != current_user_id
        ).options(selectinload(User.stores))

        if search or store_id:
            query = query.join(user_store, User.id == user_store.c.user_id, isouter=True) \
                         .join(Store, user_store.c.store_id == Store.id, isouter=True)

        if search:
            search_term = f'%{search.lower()}%'
            query = query.filter(or_(
                User.name.ilike(search_term),
                User.email.ilike(search_term),
                Store.name.ilike(search_term)
            ))

        if store_id:
            # Verify merchant has access to the store
            has_access = db.session.query(user_store).filter(
                user_store.c.user_id == current_user_id,
                user_store.c.store_id == store_id
            ).first()
            if not has_access:
                logger.warning(f"Unauthorized store access: store_id {store_id} by user ID: {current_user_id}")
                return jsonify({'status': 'error', 'message': 'Unauthorized access to store'}), 403
            query = query.filter(Store.id == store_id)

        total = query.count()
        pages = (total + per_page - 1) // per_page
        admins = query.order_by(User.name.asc()).offset((page - 1) * per_page).limit(per_page).all()
        admins_data = users_schema.dump(admins)

        logger.info(f"Retrieved {len(admins_data)} admins for user ID: {current_user_id}")
        return jsonify({
            'status': 'success',
            'admins': admins_data,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': pages
        }), 200

    except SQLAlchemyError as e:
        logger.error(f"Database error fetching admins for user ID {current_user_id}: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Database error'}), 500
    except Exception as e:
        logger.error(f"Error fetching admins for user ID {current_user_id}: {type(e).__name__} - {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@users_bp.route('/<int:user_id>', methods=['PUT'])
@jwt_required()
@role_required([UserRole.MERCHANT])
def update_user(user_id):
    """
    Update user details (name, email, stores).
    Body:
        - name (str, optional): New name
        - email (str, optional): New email
        - store_ids (list[int], optional): List of store IDs
    Responses:
        - 200: User updated successfully
        - 400: Validation error or missing fields
        - 403: Unauthorized (non-merchant user or invalid store)
        - 404: User or store not found
        - 409: Email already in use
        - 500: Internal server error
    """
    try:
        identity = get_jwt_identity()
        current_user_id = identity['id']
        data = request.get_json() or {}
        logger.info(f"Updating user ID {user_id} by user ID: {current_user_id}")

        if not data or not any(k in data for k in ('name', 'email', 'store_ids')):
            logger.error(f"Missing required fields in update request by user ID: {current_user_id}")
            return jsonify({'status': 'error', 'message': 'Name, email, or store_ids required'}), 400

        user = db.session.query(User).options(selectinload(User.stores)).filter_by(id=user_id, role=UserRole.ADMIN).first()
        if not user:
            logger.warning(f"User ID {user_id} not found or not an admin for update by user ID: {current_user_id}")
            return jsonify({'status': 'error', 'message': 'Admin not found'}), 404

        current_user = db.session.query(User).options(selectinload(User.stores)).get(current_user_id)
        if not current_user:
            logger.error(f"Current user ID {current_user_id} not found")
            return jsonify({'status': 'error', 'message': 'Current user not found'}), 404

        try:
            with db.session.begin_nested():
                if 'name' in data:
                    user.name = data['name'].strip()
                if 'email' in data:
                    new_email = data['email'].lower().strip()
                    if new_email != user.email:
                        if db.session.query(User).filter(User.email == new_email, User.id != user_id).first():
                            logger.error(f"Email {new_email} already in use")
                            return jsonify({'status': 'error', 'message': 'Email already in use'}), 409
                        user.email = new_email
                if 'store_ids' in data:
                    if not isinstance(data['store_ids'], list):
                        logger.error(f"Invalid store_ids format by user ID: {current_user_id}")
                        return jsonify({'status': 'error', 'message': 'store_ids must be a list'}), 400
                    requested_stores = db.session.query(Store).filter(Store.id.in_(data['store_ids'])).all()
                    if len(requested_stores) != len(data['store_ids']):
                        logger.warning(f"Invalid store IDs provided by user ID: {current_user_id}")
                        return jsonify({'status': 'error', 'message': 'One or more store IDs are invalid'}), 400
                    if not all(store in current_user.stores for store in requested_stores):
                        logger.warning(f"Unauthorized store access by user ID: {current_user_id}")
                        return jsonify({'status': 'error', 'message': 'Unauthorized to assign one or more stores'}), 403
                    db.session.execute(user_store.delete().where(user_store.c.user_id == user_id))
                    for store_id in data['store_ids']:
                        db.session.execute(user_store.insert().values(user_id=user_id, store_id=store_id))

                user.updated_at = datetime.utcnow()
                db.session.flush()

                notification = Notification(
                    user_id=user_id,
                    message=f"Your account details have been updated by {current_user.name}.",
                    type=NotificationType.ACCOUNT_STATUS,
                    created_at=datetime.utcnow()
                )
                db.session.add(notification)
                db.session.flush()

                updated_user = db.session.query(User).options(selectinload(User.stores)).get(user_id)
                user_data = user_schema.dump(updated_user)

                socketio.emit('user_updated', user_data, namespace='/')
                socketio.emit('new_notification', {
                    'id': notification.id,
                    'user_id': user_id,
                    'message': notification.message,
                    'type': notification.type.name,
                    'created_at': notification.created_at.isoformat()
                }, room=f'user_{user_id}')

            db.session.commit()
            logger.info(f"User ID {user_id} updated by user ID: {current_user_id}")
            return jsonify({
                'status': 'success',
                'message': 'Admin updated successfully',
                'user': user_data
            }), 200

        except ValidationError as ve:
            logger.error(f"Validation error updating user ID {user_id}: {ve.messages}")
            return jsonify({'status': 'error', 'message': 'Validation error', 'errors': ve.messages}), 400
        except IntegrityError:
            db.session.rollback()
            logger.error(f"Email already in use: {data.get('email')}")
            return jsonify({'status': 'error', 'message': 'Email already in use'}), 409
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error updating user ID {user_id}: {str(e)}", exc_info=True)
            return jsonify({'status': 'error', 'message': 'Database error'}), 500

    except Exception as e:
        logger.error(f"Error updating user ID {user_id}: {type(e).__name__} - {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@users_bp.route('/<int:user_id>/status', methods=['PUT'])
@jwt_required()
@role_required([UserRole.MERCHANT])
def update_user_status(user_id):
    """
    Update user status (activate/deactivate).
    Body:
        - status (str): New status ('ACTIVE', 'INACTIVE')
    Responses:
        - 200: Status updated successfully
        - 400: Invalid status
        - 403: Unauthorized (non-merchant user)
        - 404: User not found
        - 500: Internal server error
    """
    try:
        identity = get_jwt_identity()
        current_user_id = identity['id']
        data = request.get_json() or {}
        logger.info(f"Updating status for user ID {user_id} by user ID: {current_user_id}")

        if not data or 'status' not in data:
            logger.error(f"Missing status in status update request by user ID: {current_user_id}")
            return jsonify({'status': 'error', 'message': 'Status is required'}), 400

        try:
            new_status = UserStatus[data['status'].upper()]
        except KeyError:
            logger.error(f"Invalid status {data['status']} by user ID: {current_user_id}")
            return jsonify({'status': 'error', 'message': 'Invalid status'}), 400

        user = db.session.query(User).options(selectinload(User.stores)).filter_by(id=user_id, role=UserRole.ADMIN).first()
        if not user:
            logger.warning(f"User ID {user_id} not found or not an admin for status update by user ID: {current_user_id}")
            return jsonify({'status': 'error', 'message': 'Admin not found'}), 404

        if user.status == new_status:
            logger.warning(f"User ID {user_id} already in status {new_status.name} by user ID: {current_user_id}")
            return jsonify({'status': 'error', 'message': f"User is already {new_status.name.lower()}"}), 400

        try:
            with db.session.begin_nested():
                user.status = new_status
                user.updated_at = datetime.utcnow()
                db.session.flush()

                current_user = db.session.query(User).get(current_user_id)
                notification = Notification(
                    user_id=user_id,
                    message=f"Your account has been {new_status.name.lower()} by {current_user.name}.",
                    type=NotificationType.ACCOUNT_STATUS,
                    created_at=datetime.utcnow()
                )
                db.session.add(notification)
                db.session.flush()

                updated_user = db.session.query(User).options(selectinload(User.stores)).get(user_id)
                user_data = user_schema.dump(updated_user)

                socketio.emit('user_updated', user_data, namespace='/')
                socketio.emit('new_notification', {
                    'id': notification.id,
                    'user_id': user_id,
                    'message': notification.message,
                    'type': notification.type.name,
                    'created_at': notification.created_at.isoformat()
                }, room=f'user_{user_id}')

            db.session.commit()
            logger.info(f"User ID {user_id} status updated to {new_status.name} by user ID: {current_user_id}")
            return jsonify({
                'status': 'success',
                'message': f"Admin status updated to {new_status.name.lower()}",
                'user': user_data
            }), 200

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error updating user ID {user_id} status: {str(e)}", exc_info=True)
            return jsonify({'status': 'error', 'message': 'Database error'}), 500

    except Exception as e:
        logger.error(f"Error updating user ID {user_id} status: {type(e).__name__} - {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@users_bp.route('/<int:user_id>', methods=['DELETE'])
@jwt_required()
@role_required([UserRole.MERCHANT])
def delete_user(user_id):
    """
    Delete a user (admin or clerk) by removing only the user account (email and password).
    Responses:
        - 200: User deleted successfully
        - 403: Unauthorized (non-merchant user)
        - 404: User not found
        - 500: Internal server error
    """
    try:
        identity = get_jwt_identity()
        current_user_id = identity['id']
        logger.info(f"Deleting user ID {user_id} by user ID: {current_user_id}")

        user = db.session.query(User).options(selectinload(User.stores)).filter(
            User.id == user_id,
            User.role.in_([UserRole.ADMIN, UserRole.CLERK])
        ).first()
        if not user:
            logger.warning(f"User ID {user_id} not found or not an admin/clerk for deletion by user ID: {current_user_id}")
            return jsonify({'status': 'error', 'message': 'Admin or Clerk not found'}), 404

        try:
            with db.session.begin_nested():
                current_user = db.session.query(User).get(current_user_id)
                store_names = ', '.join(s.name for s in user.stores) if user.stores else 'None'
                notification = Notification(
                    user_id=current_user_id,
                    message=f"{user.role.name.title()} {user.name} for store(s) {store_names} was deleted.",
                    type=NotificationType.ACCOUNT_DELETION,
                    created_at=datetime.utcnow()
                )
                db.session.add(notification)
                db.session.flush()

                db.session.delete(user)
                db.session.flush()

                user_data = {'id': user_id}
                socketio.emit('user_deleted', user_data, namespace='/')
                socketio.emit('new_notification', {
                    'id': notification.id,
                    'user_id': current_user_id,
                    'message': notification.message,
                    'type': notification.type.name,
                    'created_at': notification.created_at.isoformat()
                }, room=f'user_{current_user_id}')

            db.session.commit()
            logger.info(f"User ID {user_id} deleted by user ID: {current_user_id}")
            return jsonify({
                'status': 'success',
                'message': f"{user.role.name.title()} deleted successfully"
            }), 200

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error deleting user ID {user_id}: {str(e)}", exc_info=True)
            return jsonify({'status': 'error', 'message': 'Database error'}), 500

    except Exception as e:
        logger.error(f"Error deleting user ID {user_id}: {type(e).__name__} - {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500