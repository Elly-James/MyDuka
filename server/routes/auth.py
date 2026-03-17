from flask import Blueprint, jsonify, request, url_for
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity,
    get_jwt,
    create_refresh_token
)
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db, mail, socketio
from models import User, UserRole, UserStatus, Invitation, PasswordReset, Notification, NotificationType, user_store, Store, InvitationStatus
from schemas import UserSchema, InvitationSchema, PasswordResetSchema
from datetime import datetime, timedelta
import logging
import secrets
import json
from flask_mail import Message
from config import Config
import requests
import jwt
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import selectinload
from marshmallow import ValidationError
from functools import wraps

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def get_identity():
    """
    Safely get the current JWT identity as a dict.
    Works regardless of whether the monkey-patch in app.py is active,
    by reading directly from the raw JWT claims.
    """
    raw = get_jwt().get('sub', '{}')
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            pass
    if isinstance(raw, dict):
        return raw
    return {}


# Role-based authorization decorator
def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            identity = get_identity()
            current_user_role = identity.get('role')
            if not current_user_role or UserRole[current_user_role] not in allowed_roles:
                logger.warning(f"Unauthorized access attempt by user ID: {identity.get('id')} with role: {current_user_role}")
                return jsonify({'status': 'error', 'message': 'Insufficient permissions'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


user_schema = UserSchema()
invitation_schema = InvitationSchema()
password_reset_schema = PasswordResetSchema()


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    try:
        current_user_id = get_identity().get('id')
        user = db.session.get(User, current_user_id)
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        new_token = create_access_token(identity=user)
        logger.info(f"Token refreshed for user ID: {current_user_id}")
        return jsonify({
            'status': 'success',
            'access_token': new_token
        }), 200
    except Exception as e:
        logger.error(f"Token refresh failed: {type(e).__name__} - {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Invalid refresh token'}), 401


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Handle both token verification (GET) and registration (POST)"""
    try:
        if request.method == 'GET':
            token = request.args.get('token')
            email = request.args.get('email')

            if not token or not email:
                return jsonify({'status': 'error', 'message': 'Invalid registration link - missing token or email', 'code': 'INVALID_LINK'}), 400

            invitation = db.session.query(Invitation).filter_by(token=token, email=email.lower()).first()

            if not invitation:
                return jsonify({'status': 'error', 'message': 'Invalid invitation link', 'code': 'INVALID_TOKEN'}), 400
            if invitation.is_used:
                return jsonify({'status': 'error', 'message': 'This invitation has already been used', 'code': 'USED_TOKEN'}), 400
            if invitation.expires_at < datetime.utcnow():
                return jsonify({'status': 'error', 'message': 'This invitation has expired', 'code': 'EXPIRED_TOKEN'}), 400
            if invitation.status != InvitationStatus.PENDING:
                return jsonify({'status': 'error', 'message': 'This invitation is no longer valid', 'code': 'INVALID_STATUS'}), 400

            return jsonify({
                'status': 'success',
                'message': 'Valid invitation',
                'email': email,
                'invitation': invitation_schema.dump(invitation)
            }), 200

        elif request.method == 'POST':
            data = request.get_json() or {}
            required_fields = ['token', 'email', 'name', 'password']
            if not all(k in data for k in required_fields):
                return jsonify({'status': 'error', 'message': 'All fields are required: ' + ', '.join(required_fields), 'code': 'MISSING_FIELDS'}), 400

            try:
                user_schema.validate({'email': data['email'], 'name': data['name']})
            except ValidationError as ve:
                return jsonify({'status': 'error', 'message': 'Validation error', 'errors': ve.messages, 'code': 'VALIDATION_ERROR'}), 400

            invitation = db.session.query(Invitation).filter_by(token=data['token'], email=data['email'].lower()).first()

            if not invitation:
                return jsonify({'status': 'error', 'message': 'Invalid invitation token', 'code': 'INVALID_TOKEN'}), 400
            if invitation.is_used or invitation.status != InvitationStatus.PENDING:
                return jsonify({'status': 'error', 'message': 'Invitation already used or expired', 'code': 'USED_TOKEN'}), 400
            if invitation.expires_at < datetime.utcnow():
                invitation.status = InvitationStatus.EXPIRED
                db.session.commit()
                return jsonify({'status': 'error', 'message': 'Invitation has expired', 'code': 'EXPIRED_TOKEN'}), 400

            if db.session.query(User).filter_by(email=data['email'].lower()).first():
                return jsonify({'status': 'error', 'message': 'Email already registered', 'code': 'EMAIL_EXISTS'}), 409

            try:
                with db.session.begin_nested():
                    user = User(
                        email=data['email'].lower(),
                        name=data['name'].strip(),
                        role=invitation.role,
                        status=UserStatus.ACTIVE,
                        _password=generate_password_hash(data['password']),
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    db.session.add(user)
                    invitation.is_used = True
                    invitation.status = InvitationStatus.ACCEPTED
                    invitation.updated_at = datetime.utcnow()

                    if invitation.store_id:
                        db.session.execute(user_store.insert().values(user_id=user.id, store_id=invitation.store_id))

                    notification = Notification(
                        user_id=user.id,
                        message=f"Welcome! Your {invitation.role.name.lower()} account is ready.",
                        type=NotificationType.ACCOUNT_STATUS,
                        created_at=datetime.utcnow()
                    )
                    db.session.add(notification)
                    db.session.flush()

                    user = db.session.query(User).options(selectinload(User.stores)).get(user.id)
                    user_data = user_schema.dump(user)
                    user_data['role'] = user.role.name
                    user_data['status'] = user.status.name

                    socketio.emit('user_created', user_data, namespace='/')

                db.session.commit()

                access_token = create_access_token(identity=user)
                refresh_token = create_refresh_token(identity=user)

                return jsonify({
                    'status': 'success',
                    'message': 'Registration successful',
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'user': user_data,
                    'redirect_to': f'/{user.role.name.lower()}-dashboard'
                }), 201

            except IntegrityError:
                db.session.rollback()
                return jsonify({'status': 'error', 'message': 'Email already registered', 'code': 'EMAIL_EXISTS'}), 409
            except SQLAlchemyError as e:
                db.session.rollback()
                logger.error(f"Database error: {str(e)}", exc_info=True)
                return jsonify({'status': 'error', 'message': 'Database error', 'code': 'DATABASE_ERROR'}), 500

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Internal server error', 'code': 'SERVER_ERROR'}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json() or {}
        if not all(k in data for k in ('email', 'password')):
            return jsonify({'status': 'error', 'message': 'Missing email or password'}), 400

        user = db.session.query(User).options(selectinload(User.stores)).filter_by(email=data['email'].lower()).first()
        if not user or not user.check_password(data['password']):
            return jsonify({'status': 'error', 'message': 'Invalid credentials'}), 401

        if user.status == UserStatus.INACTIVE:
            return jsonify({'status': 'error', 'message': 'Account is inactive'}), 403

        user_data = user_schema.dump(user)
        first_store = user.stores[0] if user.stores else None
        user_data['store'] = {'id': first_store.id, 'name': first_store.name} if first_store else None
        user_data.pop('stores', None)
        user_data['role'] = user.role.name
        user_data['status'] = user.status.name

        access_token = create_access_token(identity=user)
        refresh_token = create_refresh_token(identity=user)

        logger.info(f"User logged in: {user.email}, ID: {user.id}")
        return jsonify({
            'status': 'success',
            'message': 'Login successful',
            'access_token': access_token,
            'refresh_token': refresh_token,
            'redirect_to': f'/{user.role.name.lower()}-dashboard',
            'user': user_data
        }), 200

    except SQLAlchemyError as e:
        logger.error(f"Database error during login: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Database error'}), 500
    except Exception as e:
        logger.error(f"Error during login: {type(e).__name__} - {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


@auth_bp.route('/invite', methods=['POST'])
@jwt_required()
@role_required([UserRole.MERCHANT, UserRole.ADMIN])
def invite_user():
    current_user_id = None
    try:
        identity = get_identity()
        current_user_id = identity.get('id')
        current_user_role = identity.get('role')

        current_user = db.session.query(User).options(selectinload(User.stores)).get(current_user_id)
        if not current_user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404

        data = request.get_json() or {}
        if not all(k in data for k in ('email', 'role', 'store_id', 'name')):
            return jsonify({'status': 'error', 'message': 'Name, email, role, and store_id are required'}), 400

        try:
            user_schema.validate({'email': data['email'], 'name': data['name']})
        except ValidationError as ve:
            return jsonify({'status': 'error', 'message': 'Invalid name or email format', 'errors': ve.messages}), 400

        requested_role = data['role'].upper()
        try:
            role_enum = UserRole[requested_role]
        except KeyError:
            return jsonify({'status': 'error', 'message': 'Invalid role'}), 400

        if (current_user_role == UserRole.MERCHANT.name and role_enum not in [UserRole.ADMIN, UserRole.CLERK]) or \
           (current_user_role == UserRole.ADMIN.name and role_enum != UserRole.CLERK):
            return jsonify({'status': 'error', 'message': 'Unauthorized to invite users with this role'}), 403

        if db.session.query(User).filter_by(email=data['email'].lower()).first():
            return jsonify({'status': 'error', 'message': 'Email already in use'}), 409

        existing_invitation = db.session.query(Invitation).filter_by(email=data['email'].lower(), is_used=False).first()
        if existing_invitation:
            return jsonify({'status': 'error', 'message': 'An active invitation for this email already exists'}), 400

        store_id = data.get('store_id')
        store = db.session.get(Store, store_id)
        if not store or store not in current_user.stores:
            return jsonify({'status': 'error', 'message': 'Invalid or unauthorized store'}), 403

        try:
            with db.session.begin_nested():
                token = secrets.token_urlsafe(32)
                invitation = Invitation(
                    email=data['email'].lower(),
                    token=token,
                    role=role_enum,
                    creator_id=current_user_id,
                    store_id=store_id,
                    status=InvitationStatus.PENDING,
                    expires_at=datetime.utcnow() + Config.INVITATION_EXPIRY,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.session.add(invitation)

                notification = Notification(
                    user_id=current_user_id,
                    message=f"You have invited {data['name']} ({data['email']}) as a {role_enum.name.lower()} for store {store.name}.",
                    type=NotificationType.USER_INVITED,
                    created_at=datetime.utcnow()
                )
                db.session.add(notification)
                db.session.flush()

                registration_link = url_for('auth.register', _external=True) + f"?token={token}&email={data['email'].lower()}"
                msg = Message("MyDuka - Account Invitation", recipients=[data['email']], sender=Config.MAIL_DEFAULT_SENDER)
                msg.html = f"""
                <html><body>
                    <h2>Welcome to MyDuka!</h2>
                    <p>You have been invited to join MyDuka as a {role_enum.name.lower()} for store {store.name}.</p>
                    <p>Click the link below to complete your registration:</p>
                    <a href="{registration_link}" style="padding:10px;background-color:#2E3A8C;color:white;text-decoration:none;">Register Now</a>
                    <p>This link will expire in {Config.INVITATION_EXPIRY.days} days.</p>
                    <p>Regards,<br>MyDuka Team</p>
                </body></html>
                """
                try:
                    mail.send(msg)
                except Exception as mail_err:
                    logger.error(f"Failed to send invitation email to {data['email']}: {str(mail_err)}", exc_info=True)
                    db.session.rollback()
                    return jsonify({'status': 'error', 'message': 'Failed to send invitation email. Please check email configuration.'}), 500

                invitation_data = invitation_schema.dump(invitation)
                socketio.emit('user_invited', {'name': data['name'], 'email': data['email'].lower(), 'role': role_enum.name, 'store': {'id': store.id, 'name': store.name}}, namespace='/')

            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Invitation sent successfully', 'invitation': invitation_data, 'registration_link': registration_link}), 201

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error sending invitation: {str(e)}", exc_info=True)
            return jsonify({'status': 'error', 'message': 'Database error'}), 500

    except Exception as e:
        logger.error(f"Error in invite_user for user ID {current_user_id}: {type(e).__name__} - {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    try:
        data = request.get_json() or {}
        if not data.get('email'):
            return jsonify({'status': 'error', 'message': 'Email is required'}), 400

        user = db.session.query(User).filter_by(email=data['email'].lower()).first()
        if not user:
            return jsonify({'status': 'success', 'message': 'If the email exists, a reset link has been sent'}), 200

        try:
            with db.session.begin_nested():
                token = secrets.token_urlsafe(32)
                reset = PasswordReset(
                    user_id=user.id,
                    token=token,
                    expires_at=datetime.utcnow() + timedelta(hours=1),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.session.add(reset)
                db.session.flush()

                reset_link = url_for('auth.reset_password', _external=True) + f"?token={token}"
                msg = Message("MyDuka - Password Reset Request", recipients=[data['email']], sender=Config.MAIL_DEFAULT_SENDER)
                msg.html = f"""
                <html><body>
                    <h2>Password Reset Request</h2>
                    <p>Click the link below to reset your password:</p>
                    <a href="{reset_link}" style="padding:10px;background-color:#2E3A8C;color:white;text-decoration:none;">Reset Password</a>
                    <p>This link will expire in 1 hour.</p>
                    <p>Regards,<br>MyDuka Team</p>
                </body></html>
                """
                try:
                    mail.send(msg)
                except Exception as mail_err:
                    logger.error(f"Failed to send reset email: {str(mail_err)}", exc_info=True)
                    return jsonify({'status': 'error', 'message': 'Failed to send password reset email'}), 500

            db.session.commit()
            return jsonify({'status': 'success', 'message': 'If the email exists, a reset link has been sent'}), 200

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error in forgot_password: {str(e)}", exc_info=True)
            return jsonify({'status': 'success', 'message': 'If the email exists, a reset link has been sent'}), 200

    except Exception as e:
        logger.error(f"Error in forgot_password: {type(e).__name__} - {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    try:
        data = request.get_json() or {}
        if not all(k in data for k in ('token', 'password')):
            return jsonify({'status': 'error', 'message': 'Token and new password are required'}), 400

        reset = db.session.query(PasswordReset).filter_by(token=data['token']).first()
        if not reset or reset.is_used or reset.expires_at < datetime.utcnow():
            return jsonify({'status': 'error', 'message': 'Invalid or expired reset token'}), 400

        user = db.session.get(User, reset.user_id)
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404

        try:
            with db.session.begin_nested():
                user._password = generate_password_hash(data['password'])
                reset.is_used = True
                user.updated_at = datetime.utcnow()
                db.session.flush()

                notification = Notification(
                    user_id=user.id,
                    message="Your password has been successfully reset.",
                    type=NotificationType.ACCOUNT_STATUS,
                    created_at=datetime.utcnow()
                )
                db.session.add(notification)
                db.session.flush()

                socketio.emit('new_notification', {
                    'id': notification.id,
                    'user_id': user.id,
                    'message': notification.message,
                    'type': notification.type.name,
                    'created_at': notification.created_at.isoformat()
                }, room=f'user_{user.id}')

            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Password reset successfully'}), 200

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error resetting password: {str(e)}", exc_info=True)
            return jsonify({'status': 'error', 'message': 'Database error'}), 500

    except Exception as e:
        logger.error(f"Error in reset_password: {type(e).__name__} - {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """
    Get information about the current authenticated user.
    Uses get_identity() which reads directly from JWT claims,
    bypassing any import-time issues with the monkey-patch.
    """
    current_user_id = None
    try:
        identity = get_identity()
        current_user_id = identity.get('id')

        if not current_user_id:
            logger.error("No user ID found in JWT identity")
            return jsonify({'status': 'error', 'message': 'Invalid token'}), 401

        user = db.session.query(User).options(selectinload(User.stores)).get(current_user_id)
        if not user:
            logger.error(f"User not found: {current_user_id}")
            return jsonify({'status': 'error', 'message': 'User not found'}), 404

        user_data = user_schema.dump(user)
        first_store = user.stores[0] if user.stores else None
        user_data['store'] = {'id': first_store.id, 'name': first_store.name} if first_store else None
        user_data.pop('stores', None)
        user_data['role'] = user.role.name
        user_data['status'] = user.status.name

        logger.info(f"Retrieved profile for user ID: {current_user_id}")
        return jsonify({
            'status': 'success',
            'user': user_data
        }), 200

    except SQLAlchemyError as e:
        logger.error(f"Database error in get_current_user for user ID {current_user_id}: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Database error'}), 500
    except Exception as e:
        logger.error(f"Error in get_current_user for user ID {current_user_id}: {type(e).__name__} - {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


@auth_bp.route('/google', methods=['GET'])
def google_login():
    try:
        google_auth_url = (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={Config.GOOGLE_CLIENT_ID}&"
            f"redirect_uri={Config.GOOGLE_REDIRECT_URI}&"
            f"response_type=code&"
            f"scope=openid%20email%20profile&"
            f"access_type=offline"
        )
        return jsonify({'status': 'success', 'google_auth_url': google_auth_url}), 200
    except Exception as e:
        logger.error(f"Error initiating Google login: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


@auth_bp.route('/google/callback', methods=['GET'])
def google_callback():
    try:
        code = request.args.get('code')
        if not code:
            return jsonify({'status': 'error', 'message': 'Missing authorization code'}), 400

        token_url = "https://oauth2.googleapis.com/token"
        payload = {
            'code': code,
            'client_id': Config.GOOGLE_CLIENT_ID,
            'client_secret': Config.GOOGLE_CLIENT_SECRET,
            'redirect_uri': Config.GOOGLE_REDIRECT_URI,
            'grant_type': 'authorization_code'
        }
        response = requests.post(token_url, data=payload, timeout=10)
        if response.status_code != 200:
            return jsonify({'status': 'error', 'message': 'Failed to authenticate with Google'}), 400

        tokens = response.json()
        id_token = tokens.get('id_token')
        if not id_token:
            return jsonify({'status': 'error', 'message': 'Invalid Google response'}), 400

        try:
            decoded_token = jwt.decode(id_token, options={"verify_signature": False})
            email = decoded_token.get('email')
            name = decoded_token.get('name')
            if not email:
                return jsonify({'status': 'error', 'message': 'Invalid Google token'}), 400
        except jwt.InvalidTokenError as e:
            return jsonify({'status': 'error', 'message': 'Invalid Google token'}), 400

        user = db.session.query(User).options(selectinload(User.stores)).filter_by(email=email.lower()).first()
        if not user:
            try:
                with db.session.begin_nested():
                    user = User(
                        email=email.lower(),
                        name=name or email.split('@')[0],
                        role=UserRole.CLERK,
                        status=UserStatus.ACTIVE,
                        _password='',
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    db.session.add(user)
                    db.session.flush()

                    notification = Notification(
                        user_id=user.id,
                        message=f"Welcome to MyDuka! Your account was created via Google.",
                        type=NotificationType.ACCOUNT_STATUS,
                        created_at=datetime.utcnow()
                    )
                    db.session.add(notification)
                    db.session.flush()
                    socketio.emit('user_created', {'id': user.id, 'name': user.name, 'email': user.email, 'role': user.role.name}, namespace='/')

                db.session.commit()
            except SQLAlchemyError as e:
                db.session.rollback()
                logger.error(f"Database error registering Google user: {str(e)}", exc_info=True)
                return jsonify({'status': 'error', 'message': 'Database error'}), 500

        if user.status == UserStatus.INACTIVE:
            return jsonify({'status': 'error', 'message': 'Account is inactive'}), 403

        user_data = user_schema.dump(user)
        first_store = user.stores[0] if user.stores else None
        user_data['store'] = {'id': first_store.id, 'name': first_store.name} if first_store else None
        user_data.pop('stores', None)
        user_data['role'] = user.role.name
        user_data['status'] = user.status.name

        access_token = create_access_token(identity=user)
        refresh_token = create_refresh_token(identity=user)

        return jsonify({
            'status': 'success',
            'message': 'Google login successful',
            'access_token': access_token,
            'refresh_token': refresh_token,
            'redirect_to': f'/{user.role.name.lower()}-dashboard',
            'user': user_data
        }), 200

    except SQLAlchemyError as e:
        logger.error(f"Database error in google_callback: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Database error'}), 500
    except Exception as e:
        logger.error(f"Error in google_callback: {type(e).__name__} - {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500