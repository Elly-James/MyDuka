# routes/users.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from extensions import db
from models import User, UserRole, UserStatus, Store

users_bp = Blueprint('users', __name__)

@users_bp.route('', methods=['GET'])  # Removed trailing slash
@jwt_required()
def get_users():
    """Get users list with filters"""
    current_user_id = get_jwt_identity()['id']
    current_user = db.session.get(User, current_user_id)  # Updated to use Session.get()
    
    if not current_user:
        return jsonify({
            'status': 'error',
            'message': 'User not found'
        }), 404
    
    # Only admin and merchant can view users
    if current_user.role == UserRole.CLERK:
        return jsonify({
            'status': 'error',
            'message': 'Unauthorized to view users'
        }), 403
    
    # Get query parameters
    role = request.args.get('role')
    store_id = request.args.get('store_id', type=int)
    status = request.args.get('status')
    
    # Build query
    query = User.query
    
    # Apply filters
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
    
    # Admins can only see users from their store
    if current_user.role == UserRole.ADMIN:
        query = query.filter_by(store_id=current_user.store_id)
    elif store_id and current_user.role == UserRole.MERCHANT:
        query = query.filter_by(store_id=store_id)
    
    # Execute query
    users = query.all()
    
    # Prepare response
    result = []
    for user in users:
        store = db.session.get(Store, user.store_id) if user.store_id else None  # Updated to use Session.get()
        result.append({
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'role': user.role.name,
            'status': user.status.name,
            'store_id': user.store_id,
            'store_name': store.name if store else None,
            'created_at': user.created_at.isoformat(),
            'updated_at': user.updated_at.isoformat()
        })
    
    return jsonify({
        'status': 'success',
        'users': result
    }), 200

@users_bp.route('/<int:user_id>/status', methods=['PUT'])
@jwt_required()
def update_user_status(user_id):
    """Update user status (activate/deactivate)"""
    current_user_id = get_jwt_identity()['id']
    current_user = db.session.get(User, current_user_id)  # Updated to use Session.get()
    
    if not current_user:
        return jsonify({
            'status': 'error',
            'message': 'User not found'
        }), 404
    
    # Only admin and merchant can update status
    if current_user.role == UserRole.CLERK:
        return jsonify({
            'status': 'error',
            'message': 'Unauthorized to update user status'
        }), 403
    
    target_user = db.session.get(User, user_id)  # Updated to use Session.get()
    if not target_user:
        return jsonify({
            'status': 'error',
            'message': 'Target user not found'
        }), 404
    
    # Validate permissions
    if current_user.role == UserRole.ADMIN:
        # Admins can only manage clerks in their store
        if target_user.role != UserRole.CLERK or target_user.store_id != current_user.store_id:
            return jsonify({
                'status': 'error',
                'message': 'You can only manage clerks in your store'
            }), 403
    elif current_user.role == UserRole.MERCHANT:
        # Merchants can only manage admins
        if target_user.role != UserRole.ADMIN:
            return jsonify({
                'status': 'error',
                'message': 'You can only manage admins'
            }), 403
    
    data = request.get_json()
    if not data or not data.get('status'):
        return jsonify({
            'status': 'error',
            'message': 'Status is required'
        }), 400
    
    try:
        new_status = UserStatus[data['status'].upper()]
    except KeyError:
        return jsonify({
            'status': 'error',
            'message': 'Invalid status'
        }), 400
    
    target_user.status = new_status
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': f'User status updated to {new_status.name.lower()} successfully'
    }), 200

@users_bp.route('/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    """Delete a user"""
    current_user_id = get_jwt_identity()['id']
    current_user = db.session.get(User, current_user_id)  # Updated to use Session.get()
    
    if not current_user:
        return jsonify({
            'status': 'error',
            'message': 'User not found'
        }), 404
    
    # Only admin and merchant can delete users
    if current_user.role == UserRole.CLERK:
        return jsonify({
            'status': 'error',
            'message': 'Unauthorized to delete users'
        }), 403
    
    target_user = db.session.get(User, user_id)  # Updated to use Session.get()
    if not target_user:
        return jsonify({
            'status': 'error',
            'message': 'Target user not found'
        }), 404
    
    # Validate permissions
    if current_user.role == UserRole.ADMIN:
        # Admins can only delete clerks in their store
        if target_user.role != UserRole.CLERK or target_user.store_id != current_user.store_id:
            return jsonify({
                'status': 'error',
                'message': 'You can only delete clerks in your store'
            }), 403
    elif current_user.role == UserRole.MERCHANT:
        # Merchants can only delete admins
        if target_user.role != UserRole.ADMIN:
            return jsonify({
                'status': 'error',
                'message': 'You can only delete admins'
            }), 403
    
    db.session.delete(target_user)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': 'User deleted successfully'
    }), 200