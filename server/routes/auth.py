# routes/auth.py
from flask import Blueprint, request, jsonify, current_app, url_for
from werkzeug.security import check_password_hash
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity
)
import uuid
from datetime import datetime, timedelta

from extensions import db, mail
from models import User, Invitation, UserRole, UserStatus, Store
from flask_mail import Message

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    """User login endpoint"""
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({
            'status': 'error',
            'message': 'Email and password are required'
        }), 400
    
    user = User.query.filter_by(email=data['email']).first()
    
    if not user or not user.check_password(data['password']):
        return jsonify({
            'status': 'error',
            'message': 'Invalid email or password'
        }), 401
    
    if user.status == UserStatus.INACTIVE:
        return jsonify({
            'status': 'error',
            'message': 'Account is inactive. Please contact administrator.'
        }), 403
    
    # Create access token
    access_token = create_access_token(
        identity={'id': user.id, 'role': user.role.value, 'store_id': user.store_id}
    )
    
    return jsonify({
        'status': 'success',
        'message': 'Login successful',
        'access_token': access_token,
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'role': user.role.name,
            'store_id': user.store_id
        }
    }), 200

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user with invitation token"""
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password') or not data.get('name') or not data.get('token'):
        return jsonify({
            'status': 'error',
            'message': 'Name, email, password and invitation token are required'
        }), 400
    
    # Verify invitation token
    invitation = Invitation.query.filter_by(token=data['token'], email=data['email'], is_used=False).first()
    
    if not invitation:
        return jsonify({
            'status': 'error',
            'message': 'Invalid or expired invitation token'
        }), 400
    
    # Check if token is expired
    if invitation.expires_at < datetime.utcnow():
        return jsonify({
            'status': 'error',
            'message': 'Invitation token has expired'
        }), 400
    
    # Check if user already exists
    if User.query.filter_by(email=data['email']).first():
        return jsonify({
            'status': 'error',
            'message': 'User with this email already exists'
        }), 400
    
    # Create new user
    new_user = User(
        name=data['name'],
        email=data['email'],
        role=invitation.role,
        status=UserStatus.ACTIVE,
        store_id=invitation.store_id
    )
    new_user.password = data['password']  # Assuming User model has a password setter
    
    # Mark invitation as used
    invitation.is_used = True
    
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': 'Registration successful',
        'user': {
            'id': new_user.id,
            'name': new_user.name,
            'email': new_user.email,
            'role': new_user.role.name,
            'store_id': new_user.store_id
        }
    }), 201

@auth_bp.route('/invite', methods=['POST'])
@jwt_required()
def invite_user():
    """Create an invitation for a new admin or clerk"""
    current_user_id = get_jwt_identity()['id']
    current_user = db.session.get(User, current_user_id)  # Updated to use Session.get()
    
    if not current_user:
        return jsonify({
            'status': 'error',
            'message': 'User not found'
        }), 404
    
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('role'):
        return jsonify({
            'status': 'error',
            'message': 'Email and role are required'
        }), 400
    
    # Validate role based on inviter's role
    requested_role = data.get('role').upper()
    
    # Only merchant can invite admin, admin can invite clerk
    if (current_user.role == UserRole.MERCHANT.value and requested_role != UserRole.ADMIN.name) or \
       (current_user.role == UserRole.ADMIN.value and requested_role != UserRole.CLERK.name):
        return jsonify({
            'status': 'error',
            'message': 'You are not authorized to invite users with this role'
        }), 403
    
    # Check if invitation already exists and is not used
    existing_invitation = Invitation.query.filter_by(
        email=data['email'], 
        is_used=False
    ).first()
    
    if existing_invitation:
        return jsonify({
            'status': 'error',
            'message': 'An invitation for this email already exists'
        }), 400
    
    # Generate unique token
    token = str(uuid.uuid4())
    
    # Store ID handling
    store_id = None
    if current_user.role == UserRole.ADMIN.value:
        store_id = current_user.store_id
    elif data.get('store_id'):
        # Ensure store exists
        store = db.session.get(Store, data['store_id'])  # Updated to use Session.get()
        if not store:
            return jsonify({
                'status': 'error',
                'message': 'Store not found'
            }), 404
        store_id = store.id
    
    # Create invitation
    invitation = Invitation(
        email=data['email'],
        token=token,
        role=UserRole[requested_role],
        creator_id=current_user_id,
        store_id=store_id,
        expires_at=datetime.utcnow() + current_app.config['INVITATION_EXPIRY']
    )
    
    db.session.add(invitation)
    db.session.commit()
    
    # Send invitation email (mocked for testing purposes)
    registration_link = f"{request.host_url}register?token={token}&email={data['email']}"
    
    msg = Message(
        "MyDuka - Account Invitation",
        recipients=[data['email']]
    )
    msg.body = f"""
    Hello,
    
    You have been invited to join MyDuka as a {requested_role.lower()}.
    
    Please click the link below to complete your registration:
    {registration_link}
    
    This link will expire in {current_app.config['INVITATION_EXPIRY'].days} days.
    
    Regards,
    MyDuka Team
    """
    
    try:
        mail.send(msg)
    except Exception as e:
        # Log the error but don't fail the request
        current_app.logger.error(f"Error sending email: {str(e)}")
    
    return jsonify({
        'status': 'success',
        'message': 'Invitation sent successfully',
        'registration_link': registration_link
    }), 201

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current user information"""
    current_user_id = get_jwt_identity()['id']
    
    user = db.session.get(User, current_user_id)  # Updated to use Session.get()
    if not user:
        return jsonify({
            'status': 'error',
            'message': 'User not found'
        }), 404
    
    # Get store name if applicable
    store_name = None
    if user.store_id:
        store = db.session.get(Store, user.store_id)  # Updated to use Session.get()
        if store:
            store_name = store.name
    
    return jsonify({
        'status': 'success',
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'role': user.role.name,
            'status': user.status.name,
            'store_id': user.store_id,
            'store_name': store_name,
            'created_at': user.created_at.isoformat()
        }
    }), 200


