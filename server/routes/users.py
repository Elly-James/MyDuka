from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import selectinload, joinedload
from extensions import db, socketio
from models import User, UserRole, UserStatus, Store, Notification, NotificationType, user_store
from schemas import UserSchema
from sqlalchemy import or_, and_
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

def get_current_user():
    """Helper function to get the current user from the JWT identity"""
    identity = get_jwt_identity()
    return db.session.query(User).options(selectinload(User.stores)).get(identity['id'])

def build_user_query(current_user_id, role=None, search=None, store_id=None):
    """Helper function to build common user queries"""
    query = db.session.query(User).options(
        selectinload(User.stores)
    )
    
    if role:
        query = query.filter(User.role == role)
    
    if current_user_id:
        query = query.filter(User.id != current_user_id)
    
    if search or store_id:
        query = query.join(user_store, isouter=True).join(Store, isouter=True)
    
    if search:
        search_term = f'%{search.lower()}%'
        query = query.filter(or_(
            User.name.ilike(search_term),
            User.email.ilike(search_term),
            Store.name.ilike(search_term)
        ))
    
    if store_id:
        query = query.filter(Store.id == store_id)
    
    return query

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
        - 400: Invalid role
        - 500: Internal server error
    """
    try:
        identity = get_jwt_identity()
        current_user_id = identity['id']
        logger.debug(f"Fetching users for user ID: {current_user_id}")
        
        # Get query parameters
        role = request.args.get('role', '').strip().upper()
        search = request.args.get('search', '').strip()
        page = max(1, request.args.get('page', 1, type=int))
        per_page = max(1, request.args.get('per_page', 10, type=int))
        
        # Build base query
        query = build_user_query(current_user_id)
        
        # Apply role filter if specified
        if role:
            try:
                query = query.filter(User.role == UserRole[role])
            except KeyError:
                logger.error(f"Invalid role parameter: {role}")
                return jsonify({'status': 'error', 'message': 'Invalid role'}), 400
        
        # Apply search filter if specified
        if search:
            search_term = f'%{search.lower()}%'
            query = query.filter(or_(
                User.name.ilike(search_term),
                User.email.ilike(search_term)
            ))
        
        # Get paginated results
        total = query.count()
        pages = (total + per_page - 1) // per_page
        users = query.order_by(User.name.asc()).offset((page - 1) * per_page).limit(per_page).all()
        
        logger.info(f"Retrieved {len(users)} users for user ID: {current_user_id}")
        return jsonify({
            'status': 'success',
            'users': users_schema.dump(users),
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
        - 500: Internal server error
    """
    try:
        identity = get_jwt_identity()
        current_user_id = identity['id']
        logger.debug(f"Fetching admins for user ID: {current_user_id}")
        
        # Get query parameters
        search = request.args.get('search', '').strip()
        store_id = request.args.get('store_id', None, type=int)
        page = max(1, request.args.get('page', 1, type=int))
        per_page = max(1, request.args.get('per_page', 10, type=int))
        
        # Build query for admins
        query = build_user_query(
            current_user_id,
            role=UserRole.ADMIN,
            search=search,
            store_id=store_id
        )
        
        # Verify store access if store_id is specified
        if store_id:
            has_access = db.session.query(user_store).filter(
                user_store.c.user_id == current_user_id,
                user_store.c.store_id == store_id
            ).first()
            if not has_access:
                logger.warning(f"Unauthorized store access: store_id {store_id} by user ID: {current_user_id}")
                return jsonify({'status': 'error', 'message': 'Unauthorized access to store'}), 403
        
        # Get paginated results
        total = query.count()
        pages = (total + per_page - 1) // per_page
        admins = query.order_by(User.name.asc()).offset((page - 1) * per_page).limit(per_page).all()
        
        logger.info(f"Retrieved {len(admins)} admins for user ID: {current_user_id}")
        return jsonify({
            'status': 'success',
            'admins': users_schema.dump(admins),
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

@users_bp.route('/clerks', methods=['GET'])
@jwt_required()
@role_required([UserRole.ADMIN, UserRole.MERCHANT])
def get_clerks():
    """
    Get all clerks with associated stores.
    Query Parameters:
        - search (str, optional): Search by name, email, or store name
        - page (int, optional): Page number (default 1)
        - per_page (int, optional): Clerks per page (default 10)
    Responses:
        - 200: List of clerks with pagination
        - 403: Unauthorized (store access for merchants)
        - 500: Internal server error
    """
    try:
        identity = get_jwt_identity()
        current_user_id = identity['id']
        current_user_role = UserRole[identity['role']]
        logger.debug(f"Fetching clerks for user ID: {current_user_id}")
        
        # Get query parameters
        search = request.args.get('search', '').strip()
        page = max(1, request.args.get('page', 1, type=int))
        per_page = max(1, request.args.get('per_page', 10, type=int))
        
        # Build query for clerks
        query = build_user_query(
            current_user_id,
            role=UserRole.CLERK,
            search=search
        )
        
        # For merchants, only show clerks from their stores
        if current_user_role == UserRole.MERCHANT:
            query = query.join(user_store).filter(
                user_store.c.store_id.in_(
                    db.session.query(user_store.c.store_id).filter(
                        user_store.c.user_id == current_user_id
                    )
                )
            )
        
        # Get paginated results
        total = query.count()
        pages = (total + per_page - 1) // per_page
        clerks = query.order_by(User.name.asc()).offset((page - 1) * per_page).limit(per_page).all()
        
        logger.info(f"Retrieved {len(clerks)} clerks for user ID: {current_user_id}")
        return jsonify({
            'status': 'success',
            'clerks': users_schema.dump(clerks),
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': pages
        }), 200

    except SQLAlchemyError as e:
        logger.error(f"Database error fetching clerks for user ID {current_user_id}: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Database error'}), 500
    except Exception as e:
        logger.error(f"Error fetching clerks for user ID {current_user_id}: {type(e).__name__} - {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@users_bp.route('/<int:user_id>', methods=['PUT'])
@jwt_required()
@role_required([UserRole.MERCHANT, UserRole.ADMIN])
def update_user(user_id):
    """
    Update user details (name, email, stores).
    Now accessible to both MERCHANT and ADMIN roles.
    Body:
        - name (str, optional): New name
        - email (str, optional): New email
        - store_ids (list[int], optional): List of store IDs
    Responses:
        - 200: User updated successfully
        - 400: Validation error or missing fields
        - 403: Unauthorized (merchant updating non-clerk or invalid store)
        - 404: User not found
        - 409: Email already in use
        - 500: Internal server error
    """
    try:
        identity = get_jwt_identity()
        current_user_id = identity['id']
        current_user_role = UserRole[identity['role']]
        data = request.get_json() or {}
        logger.info(f"Updating user ID {user_id} by user ID: {current_user_id}")
        
        # Validate input
        if not data or not any(k in data for k in ('name', 'email', 'store_ids')):
            logger.error(f"Missing required fields in update request by user ID: {current_user_id}")
            return jsonify({'status': 'error', 'message': 'Name, email, or store_ids required'}), 400

        # Get user to update
        user = db.session.query(User).options(selectinload(User.stores)).get(user_id)
        if not user:
            logger.warning(f"User ID {user_id} not found for update by user ID: {current_user_id}")
            return jsonify({'status': 'error', 'message': 'User not found'}), 404

        # Authorization check
        if current_user_role == UserRole.MERCHANT:
            # Merchants can only update their own clerks
            if user.role != UserRole.CLERK:
                logger.warning(f"Merchant attempted to update non-clerk user ID {user_id}")
                return jsonify({'status': 'error', 'message': 'Can only update clerks'}), 403
            
            # Verify merchant has access to all stores being assigned
            if 'store_ids' in data:
                current_user = get_current_user()
                if not current_user:
                    logger.error(f"Current user ID {current_user_id} not found")
                    return jsonify({'status': 'error', 'message': 'Current user not found'}), 404
                merchant_store_ids = [s.id for s in current_user.stores]
                if not all(sid in merchant_store_ids for sid in data['store_ids']):
                    logger.warning(f"Unauthorized store access by user ID: {current_user_id}")
                    return jsonify({'status': 'error', 'message': 'Unauthorized store access'}), 403

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
                    db.session.execute(user_store.delete().where(user_store.c.user_id == user_id))
                    for store_id in data['store_ids']:
                        db.session.execute(user_store.insert().values(user_id=user_id, store_id=store_id))

                user.updated_at = datetime.utcnow()
                db.session.flush()
                
                current_user = get_current_user()
                if not current_user:
                    logger.error(f"Current user ID {current_user_id} not found")
                    return jsonify({'status': 'error', 'message': 'Current user not found'}), 404
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
                'message': 'User updated successfully',
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
@role_required([UserRole.MERCHANT, UserRole.ADMIN])
def update_user_status(user_id):
    """
    Update user status (activate/deactivate).
    Now accessible to both MERCHANT and ADMIN roles.
    Body:
        - status (str): New status ('ACTIVE', 'INACTIVE')
    Responses:
        - 200: Status updated successfully
        - 400: Invalid status or missing fields
        - 403: Unauthorized (merchant updating non-clerk or unauthorized access)
        - 404: User not found
        - 500: Internal server error
    """
    try:
        identity = get_jwt_identity()
        current_user_id = identity['id']
        current_user_role = UserRole[identity['role']]
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

        user = db.session.query(User).options(selectinload(User.stores)).get(user_id)
        if not user:
            logger.warning(f"User ID {user_id} not found for status update by user ID: {current_user_id}")
            return jsonify({'status': 'error', 'message': 'User not found'}), 404

        # Authorization check
        if current_user_role == UserRole.MERCHANT:
            # Merchants can only update their own clerks
            if user.role != UserRole.CLERK:
                logger.warning(f"Merchant attempted to update status of non-clerk user ID {user_id}")
                return jsonify({'status': 'error', 'message': 'Can only update clerks'}), 403
            
            # Verify merchant has access to at least one of the user's stores
            current_user = get_current_user()
            if not current_user:
                logger.error(f"Current user ID {current_user_id} not found")
                return jsonify({'status': 'error', 'message': 'Current user not found'}), 404
            merchant_store_ids = [s.id for s in current_user.stores]
            user_store_ids = [s.id for s in user.stores]
            if not any(sid in merchant_store_ids for sid in user_store_ids):
                logger.warning(f"Unauthorized store access by user ID: {current_user_id}")
                return jsonify({'status': 'error', 'message': 'Unauthorized access'}), 403

        if user.status == new_status:
            logger.warning(f"User ID {user_id} already in status {new_status.name} by user ID: {current_user_id}")
            return jsonify({'status': 'error', 'message': f"User is already {new_status.name.lower()}"}), 400

        try:
            with db.session.begin_nested():
                user.status = new_status
                user.updated_at = datetime.utcnow()
                db.session.flush()
                
                current_user = get_current_user()
                if not current_user:
                    logger.error(f"Current user ID {current_user_id} not found")
                    return jsonify({'status': 'error', 'message': 'Current user not found'}), 404
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
                'message': f"User status updated to {new_status.name.lower()}",
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
@role_required([UserRole.MERCHANT, UserRole.ADMIN])
def delete_user(user_id):
    """
    Delete a user (admin or clerk).
    Now accessible to both MERCHANT and ADMIN roles.
    Responses:
        - 200: User deleted successfully
        - 403: Unauthorized (merchant deleting non-clerk or unauthorized access)
        - 404: User not found
        - 500: Internal server error
    """
    try:
        identity = get_jwt_identity()
        current_user_id = identity['id']
        current_user_role = UserRole[identity['role']]
        logger.info(f"Deleting user ID {user_id} by user ID: {current_user_id}")

        user = db.session.query(User).options(selectinload(User.stores)).get(user_id)
        if not user:
            logger.warning(f"User ID {user_id} not found for deletion by user ID: {current_user_id}")
            return jsonify({'status': 'error', 'message': 'User not found'}), 404

        # Authorization check
        if current_user_role == UserRole.MERCHANT:
            # Merchants can only delete their own clerks
            if user.role != UserRole.CLERK:
                logger.warning(f"Merchant attempted to delete non-clerk user ID {user_id}")
                return jsonify({'status': 'error', 'message': 'Can only delete clerks'}), 403
            
            # Verify merchant has access to at least one of the user's stores
            current_user = get_current_user()
            if not current_user:
                logger.error(f"Current user ID {current_user_id} not found")
                return jsonify({'status': 'error', 'message': 'Current user not found'}), 404
            merchant_store_ids = [s.id for s in current_user.stores]
            user_store_ids = [s.id for s in user.stores]
            if not any(sid in merchant_store_ids for sid in user_store_ids):
                logger.warning(f"Unauthorized store access by user ID: {current_user_id}")
                return jsonify({'status': 'error', 'message': 'Unauthorized access'}), 403

        try:
            with db.session.begin_nested():
                current_user = get_current_user()
                if not current_user:
                    logger.error(f"Current user ID {current_user_id} not found")
                    return jsonify({'status': 'error', 'message': 'Current user not found'}), 404
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