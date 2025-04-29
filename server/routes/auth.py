from flask import Blueprint, request, jsonify, current_app, url_for, redirect
from werkzeug.security import check_password_hash, generate_password_hash
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import uuid
from datetime import datetime, timedelta
import logging
import os

from extensions import db, mail, socketio  # Added socketio import
from models import User, Invitation, UserRole, UserStatus, Store, PasswordReset, Notification  # Added Notification import
from schemas import UserSchema, InvitationSchema, PasswordResetSchema
from flask_mail import Message
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

auth_bp = Blueprint('auth', __name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100 per day", "50 per hour"]
)

# Google OAuth 2.0 Configuration
SCOPES = ['openid', 'https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile']

def get_redirect_uri():
    """Dynamically construct the redirect URI based on the environment."""
    base_url = os.getenv('BASE_URL', 'http://localhost:5000')
    return f"{base_url}/api/auth/google/callback"

@auth_bp.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    """
    User login endpoint.
    
    Request Body:
        - email (str): User's email
        - password (str): User's password
    
    Responses:
        - 200: Login successful, returns access token and user info
        - 400: Missing email or password
        - 401: Invalid email or password
        - 403: Account is inactive
        - 500: Internal server error
    """
    try:
        data = request.get_json()
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'status': 'error', 'message': 'Email and password are required'}), 400
        
        # Validate email using UserSchema
        user_data = {
            'email': data['email'],
            'name': 'placeholder',  # Temporary for validation
            'role': UserRole.MERCHANT.name,  # Temporary role
            'status': 'active'
        }
        user_schema = UserSchema()
        errors = user_schema.validate(user_data)
        if errors:
            return jsonify({
                'status': 'error',
                'message': 'Validation error',
                'errors': errors
            }), 400

        user = User.query.filter_by(email=data['email']).first()
        
        if not user or not user.check_password(data['password']):
            return jsonify({'status': 'error', 'message': 'Invalid email or password'}), 401
        
        if user.status == UserStatus.INACTIVE:
            return jsonify({'status': 'error', 'message': 'Account is inactive'}), 403
        
        access_token = create_access_token(identity=user)
        
        # Use UserSchema to serialize user data
        user_data = user_schema.dump(user)

        return jsonify({
            'status': 'success',
            'access_token': access_token,
            'redirect_to': f'/{user.role.name.lower()}-dashboard',
            'user': user_data
        }), 200
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user with an invitation token.
    
    Request Body:
        - email (str): User's email
        - password (str): User's password
        - name (str): User's name
        - token (str): Invitation token
    
    Responses:
        - 201: Registration successful
        - 400: Missing required fields, invalid token, or validation error
        - 500: Internal server error
    """
    try:
        data = request.get_json()
        if not data or not data.get('email') or not data.get('password') or not data.get('name') or not data.get('token'):
            return jsonify({
                'status': 'error',
                'message': 'Name, email, password, and invitation token are required'
            }), 400
        
        invitation = Invitation.query.filter_by(token=data['token'], email=data['email'], is_used=False).first()
        
        if not invitation:
            return jsonify({
                'status': 'error',
                'message': 'Invalid or expired invitation token'
            }), 400
        
        if invitation.expires_at < datetime.utcnow():
            return jsonify({
                'status': 'error',
                'message': 'Invitation token has expired'
            }), 400
        
        if User.query.filter_by(email=data['email']).first():
            return jsonify({
                'status': 'error',
                'message': 'User with this email already exists'
            }), 400
        
        # Validate user data using UserSchema
        user_data = {
            'email': data['email'],
            'name': data['name'],
            'role': invitation.role.name,
            'status': UserStatus.ACTIVE.name
        }
        user_schema = UserSchema()
        errors = user_schema.validate(user_data)
        if errors:
            return jsonify({
                'status': 'error',
                'message': 'Validation error',
                'errors': errors
            }), 400

        new_user = User(
            name=data['name'],
            email=data['email'],
            role=invitation.role,
            status=UserStatus.ACTIVE,
            store_id=invitation.store_id
        )
        new_user.password = data['password']  # Password hashing handled in the model
        
        invitation.is_used = True
        
        db.session.add(new_user)
        db.session.commit()
        
        # Serialize the new user data
        user_data = user_schema.dump(new_user)

        logger.info(f"User registered: {new_user.email} by invitation from IP: {get_remote_address()}")
        return jsonify({
            'status': 'success',
            'message': 'Registration successful',
            'user': user_data
        }), 201
    except Exception as e:
        logger.error(f"Error in register: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

@auth_bp.route('/invite', methods=['POST'])
@jwt_required()
def invite_user():
    """
    Create an invitation for a new admin or clerk.
    
    Request Body:
        - email (str): Email of the invited user
        - role (str): Role of the invited user (ADMIN or CLERK)
        - store_id (int, optional): Store ID for the invited user
    
    Responses:
        - 201: Invitation sent successfully
        - 400: Missing required fields, existing invitation, or validation error
        - 403: Unauthorized role invitation
        - 404: Store not found
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
        
        data = request.get_json()
        if not data or not data.get('email') or not data.get('role'):
            return jsonify({
                'status': 'error',
                'message': 'Email and role are required'
            }), 400
        
        # Validate the invitation data using InvitationSchema
        invitation_data = {
            'email': data['email'],
            'role': data.get('role').upper(),
            'creator_id': current_user_id,
            'store_id': data.get('store_id'),
            'expires_at': datetime.utcnow() + current_app.config['INVITATION_EXPIRY']
        }
        invitation_schema = InvitationSchema()
        errors = invitation_schema.validate(invitation_data)
        if errors:
            return jsonify({
                'status': 'error',
                'message': 'Validation error',
                'errors': errors
            }), 400

        requested_role = data.get('role').upper()
        if (current_user.role == UserRole.MERCHANT.value and requested_role != UserRole.ADMIN.name) or \
           (current_user.role == UserRole.ADMIN.value and requested_role != UserRole.CLERK.name):
            return jsonify({
                'status': 'error',
                'message': 'You are not authorized to invite users with this role'
            }), 403
        
        existing_invitation = Invitation.query.filter_by(
            email=data['email'], 
            is_used=False
        ).first()
        if existing_invitation:
            return jsonify({
                'status': 'error',
                'message': 'An invitation for this email already exists'
            }), 400
        
        token = str(uuid.uuid4())
        store_id = None
        if current_user.role == UserRole.ADMIN.value:
            store_id = current_user.store_id
        elif data.get('store_id'):
            store = db.session.get(Store, data['store_id'])
            if not store:
                return jsonify({
                    'status': 'error',
                    'message': 'Store not found'
                }), 404
            store_id = store.id
        
        invitation = Invitation(
            email=data['email'],
            token=token,
            role=UserRole[requested_role],
            creator_id=current_user_id,
            store_id=store_id,
            expires_at=datetime.utcnow() + current_app.config['INVITATION_EXPIRY']
        )
        
        db.session.add(invitation)
        
        # Create a notification for the inviter (current_user)
        notification = Notification(
            user_id=current_user_id,
            message=f"You have invited {data['email']} as a {requested_role.lower()}."
        )
        db.session.add(notification)
        db.session.flush()
        
        # Emit WebSocket event for the notification
        socketio.emit('new_notification', {
            'id': notification.id,
            'message': notification.message,
            'created_at': notification.created_at.isoformat()
        }, room=f'user_{current_user_id}')
        
        db.session.commit()
        
        # Serialize the invitation data
        invitation_data = invitation_schema.dump(invitation)

        registration_link = f"{request.host_url}register?token={token}&email={data['email']}"
        msg = Message(
            "MyDuka - Account Invitation",
            recipients=[data['email']]
        )
        msg.html = f"""
        <html>
            <body>
                <h2>Welcome to MyDuka!</h2>
                <p>You have been invited to join MyDuka as a {requested_role.lower()}.</p>
                <p>Please click the link below to complete your registration:</p>
                <a href="{registration_link}" style="padding: 10px; background-color: #2E3A8C; color: white; text-decoration: none;">Register Now</a>
                <p>This link will expire in {current_app.config['INVITATION_EXPIRY'].days} days.</p>
                <p>Regards,<br>MyDuka Team</p>
            </body>
        </html>
        """
        
        try:
            mail.send(msg)
            logger.info(f"Invitation sent to: {data['email']} by user ID: {current_user_id}")
        except Exception as e:
            logger.error(f"Error sending email to {data['email']}: {str(e)}")
        
        return jsonify({
            'status': 'success',
            'message': 'Invitation sent successfully',
            'invitation': invitation_data,
            'registration_link': registration_link
        }), 201
    except Exception as e:
        logger.error(f"Error in invite_user: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

@auth_bp.route('/forgot-password', methods=['POST'])
@limiter.limit("5 per minute")
def forgot_password():
    """
    Send a password reset link to the user's email.
    
    Request Body:
        - email (str): User's email
    
    Responses:
        - 200: Reset link sent (or email not found, message is generic for security)
        - 400: Missing email or validation error
        - 500: Internal server error
    """
    try:
        data = request.get_json()
        if not data or not data.get('email'):
            return jsonify({
                'status': 'error',
                'message': 'Email is required'
            }), 400
        
        # Validate the email using UserSchema
        user_data = {
            'email': data['email'],
            'name': 'placeholder',  # Temporary name for validation
            'role': UserRole.MERCHANT.name,  # Temporary role
            'status': 'active'
        }
        user_schema = UserSchema()
        errors = user_schema.validate(user_data)
        if errors:
            return jsonify({
                'status': 'error',
                'message': 'Validation error',
                'errors': errors
            }), 400

        user = User.query.filter_by(email=data['email']).first()
        if not user:
            logger.info(f"Password reset requested for non-existent email: {data['email']} from IP: {get_remote_address()}")
            return jsonify({
                'status': 'success',
                'message': 'If the email exists, a reset link has been sent'
            }), 200  # Don't reveal if email exists
        
        token = str(uuid.uuid4())
        reset = PasswordReset(
            user_id=user.id,
            token=token,
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        db.session.add(reset)
        db.session.commit()
        
        # Serialize the password reset data
        reset_schema = PasswordResetSchema()
        reset_data = reset_schema.dump(reset)

        reset_link = f"{request.host_url}reset-password?token={token}"
        msg = Message(
            "MyDuka - Password Reset Request",
            recipients=[data['email']]
        )
        msg.html = f"""
        <html>
            <body>
                <h2>Password Reset Request</h2>
                <p>You requested to reset your MyDuka password.</p>
                <p>Click the link below to reset your password:</p>
                <a href="{reset_link}" style="padding: 10px; background-color: #2E3A8C; color: white; text-decoration: none;">Reset Password</a>
                <p>This link will expire in 1 hour.</p>
                <p>If you did not request this, please ignore this email.</p>
                <p>Regards,<br>MyDuka Team</p>
            </body>
        </html>
        """
        
        try:
            mail.send(msg)
            logger.info(f"Password reset link sent to: {data['email']} for user ID: {user.id}")
        except Exception as e:
            logger.error(f"Error sending password reset email to {data['email']}: {str(e)}")
        
        return jsonify({
            'status': 'success',
            'message': 'If the email exists, a reset link has been sent',
            'reset': reset_data
        }), 200
    except Exception as e:
        logger.error(f"Error in forgot_password: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

@auth_bp.route('/reset-password', methods=['POST'])
@limiter.limit("5 per minute")
def reset_password():
    """
    Reset password using a reset token.
    
    Request Body:
        - token (str): Password reset token
        - password (str): New password
    
    Responses:
        - 200: Password reset successfully
        - 400: Missing token or password, or invalid token
        - 404: User not found
        - 500: Internal server error
    """
    try:
        data = request.get_json()
        if not data or not data.get('token') or not data.get('password'):
            return jsonify({
                'status': 'error',
                'message': 'Token and new password are required'
            }), 400
        
        reset = PasswordReset.query.filter_by(token=data['token']).first()
        if not reset or reset.is_used or reset.expires_at < datetime.utcnow():
            logger.warning(f"Invalid or expired reset token used from IP: {get_remote_address()}")
            return jsonify({
                'status': 'error',
                'message': 'Invalid or expired reset token'
            }), 400
        
        user = db.session.get(User, reset.user_id)
        if not user:
            return jsonify({
                'status': 'error',
                'message': 'User not found'
            }), 404
        
        user.password = data['password']  # Password hashing handled in the model
        reset.is_used = True
        db.session.commit()
        
        # Serialize the updated password reset data
        reset_schema = PasswordResetSchema()
        reset_data = reset_schema.dump(reset)

        logger.info(f"Password reset for user: {user.email} (ID: {user.id}) from IP: {get_remote_address()}")
        return jsonify({
            'status': 'success',
            'message': 'Password reset successfully',
            'reset': reset_data
        }), 200
    except Exception as e:
        logger.error(f"Error in reset_password: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """
    Get information about the current user.
    
    Responses:
        - 200: User information
        - 404: User not found
        - 500: Internal server error
    """
    try:
        current_user_id = get_jwt_identity()['id']
        user = db.session.get(User, current_user_id)
        if not user:
            return jsonify({
                'status': 'error',
                'message': 'User not found'
            }), 404
        
        # Use UserSchema to serialize user data
        user_schema = UserSchema()
        user_data = user_schema.dump(user)

        store_name = None
        if user.store_id:
            store = db.session.get(Store, user.store_id)
            if store:
                store_name = store.name
        
        # Add additional fields not covered by UserSchema
        user_data['store_id'] = user.store_id
        user_data['store_name'] = store_name
        user_data['created_at'] = user.created_at.isoformat()

        return jsonify({
            'status': 'success',
            'user': user_data
        }), 200
    except Exception as e:
        logger.error(f"Error in get_current_user: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

@auth_bp.route('/google/login', methods=['GET'])
def google_login():
    """
    Initiate Google OAuth 2.0 login flow.
    
    Responses:
        - 302: Redirect to Google authorization URL
        - 500: Internal server error or missing credentials
    """
    try:
        client_id = current_app.config.get('GOOGLE_CLIENT_ID')
        client_secret = current_app.config.get('GOOGLE_CLIENT_SECRET')
        
        if not client_id or not client_secret:
            logger.error("Google OAuth credentials not configured")
            return jsonify({
                'status': 'error',
                'message': 'Google OAuth credentials not configured'
            }), 500

        client_config = {
            'web': {
                'client_id': client_id,
                'client_secret': client_secret,
                'redirect_uris': [get_redirect_uri()],
                'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                'token_uri': 'https://oauth2.googleapis.com/token',
            }
        }

        flow = Flow.from_client_config(client_config, scopes=SCOPES)
        flow.redirect_uri = get_redirect_uri()

        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )

        # Store the state in the session for validation in the callback
        request.session = request.environ.get('session', {})
        request.session['state'] = state

        logger.info(f"Initiating Google OAuth login from IP: {get_remote_address()}")
        return redirect(authorization_url)

    except Exception as e:
        logger.error(f"Error in google_login: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

@auth_bp.route('/google/callback', methods=['GET'])
def google_callback():
    """
    Handle Google OAuth 2.0 callback.
    
    Query Parameters:
        - code (str): Authorization code from Google
        - state (str): State parameter for CSRF protection
    
    Responses:
        - 200: Google login successful, returns access token and user info
        - 400: Invalid state parameter or failed to retrieve email
        - 500: Internal server error
    """
    try:
        # Retrieve the state from the session
        request.session = request.environ.get('session', {})
        state = request.session.get('state')
        if not state or state != request.args.get('state'):
            logger.warning(f"Invalid state parameter in Google OAuth callback from IP: {get_remote_address()}")
            return jsonify({
                'status': 'error',
                'message': 'Invalid state parameter'
            }), 400

        client_id = current_app.config.get('GOOGLE_CLIENT_ID')
        client_secret = current_app.config.get('GOOGLE_CLIENT_SECRET')

        client_config = {
            'web': {
                'client_id': client_id,
                'client_secret': client_secret,
                'redirect_uris': [get_redirect_uri()],
                'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                'token_uri': 'https://oauth2.googleapis.com/token',
            }
        }

        flow = Flow.from_client_config(client_config, scopes=SCOPES, state=state)
        flow.redirect_uri = get_redirect_uri()

        try:
            authorization_response = request.url
            flow.fetch_token(authorization_response=authorization_response)
        except Exception as e:
            logger.error(f"Failed to fetch Google OAuth token: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'Failed to authenticate with Google: ' + str(e)
            }), 400

        credentials = flow.credentials
        try:
            service = build('oauth2', 'v2', credentials=credentials)
            user_info = service.userinfo().get().execute()
        except HttpError as e:
            logger.error(f"Failed to retrieve user info from Google: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'Failed to retrieve user information from Google'
            }), 400

        email = user_info.get('email')
        name = user_info.get('name')

        if not email:
            logger.warning(f"Failed to retrieve email from Google for user from IP: {get_remote_address()}")
            return jsonify({
                'status': 'error',
                'message': 'Failed to retrieve email from Google'
            }), 400

        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(
                email=email,
                name=name,
                role=UserRole.CLERK,
                status=UserStatus.ACTIVE,
                store_id=None
            )
            user.password = ''  # No password for Google login users
            db.session.add(user)
            db.session.commit()
            logger.info(f"User registered via Google: {email} (ID: {user.id})")

        access_token = create_access_token(
            identity={'id': user.id, 'role': user.role.value, 'store_id': user.store_id}
        )

        # Use UserSchema to serialize user data
        user_schema = UserSchema()
        user_data = user_schema.dump(user)

        # Add store_id which isn't part of UserSchema
        user_data['store_id'] = user.store_id

        logger.info(f"User logged in via Google: {email} (ID: {user.id}) from IP: {get_remote_address()}")
        return jsonify({
            'status': 'success',
            'message': 'Google login successful',
            'access_token': access_token,
            'user': user_data
        }), 200

    except Exception as e:
        logger.error(f"Error in google_callback: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500