from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from models import Store, User, UserRole, InventoryEntry, SalesRecord, Product, PaymentStatus, user_store
from schemas import StoreSchema, StoreDetailSchema
from sqlalchemy import func
from sqlalchemy.sql.expression import case
from datetime import datetime, timedelta
import logging
from functools import wraps
import calendar

stores_bp = Blueprint('stores', __name__, url_prefix='/api/stores')

# Configure logging
logging.basicConfig(level=logging.DEBUG)  # Changed to DEBUG for detailed tracing
logger = logging.getLogger(__name__)

def role_required(roles):
    """Decorator to restrict access to specific roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            identity = get_jwt_identity()
            current_user_role = identity['role']
            if current_user_role not in [role.name for role in roles]:
                logger.warning(f"Unauthorized access attempt by user ID: {identity['id']}, role: {current_user_role}")
                return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_period_dates(period, week_start='monday'):
    """Helper function to get date ranges for reporting periods"""
    today = datetime.utcnow().replace(hour=23, minute=59, second=59, microsecond=999999)
    if period == 'weekly':
        week_start_day = 0 if week_start.lower() == 'monday' else 6
        days_since_start = (today.weekday() - week_start_day) % 7
        start = today - timedelta(days=days_since_start)
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=6)
    elif period == 'monthly':
        start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_day = calendar.monthrange(today.year, today.month)[1]
        end = start.replace(day=last_day, hour=23, minute=59, second=59, microsecond=999999)
    elif period == 'annual':
        start = today.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = today.replace(month=12, day=31, hour=23, minute=59, second=59, microsecond=999999)
    else:
        start = today - timedelta(days=30)
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = today
    return start, end

@stores_bp.route('', methods=['GET'])
@jwt_required()
@role_required([UserRole.MERCHANT, UserRole.ADMIN])
def get_stores():
    """
    Get a list of all stores with basic information.
    For merchants: returns all stores they are associated with via user_store
    For admins: returns only their associated stores
    Responses:
        - 200: List of stores
        - 404: User not found
        - 500: Internal server error
    """
    try:
        identity = get_jwt_identity()
        current_user_id = identity['id']
        current_user_role = identity['role']
        logger.debug(f"Fetching stores for user ID: {current_user_id}, role: {current_user_role}")

        current_user = db.session.get(User, current_user_id)
        if not current_user:
            logger.error(f"User not found: {current_user_id}")
            return jsonify({'status': 'error', 'message': 'User not found'}), 404

        stores_query = (
            db.session.query(Store)
            .join(user_store, Store.id == user_store.c.store_id)
            .filter(user_store.c.user_id == current_user_id)
        )

        stores = stores_query.order_by(Store.name.asc()).all()
        stores_data = StoreSchema(many=True).dump(stores)
        if not stores:
            logger.warning(f"No stores found for user ID: {current_user_id}, role: {current_user_role}")
            return jsonify({
                'status': 'success',
                'message': 'No stores associated with this user',
                'stores': []
            }), 200

        logger.info(f"Retrieved {len(stores)} stores for user ID: {current_user_id}")
        return jsonify({
            'status': 'success',
            'stores': stores_data
        }), 200

    except Exception as e:
        logger.error(f"Error fetching stores for user ID {current_user_id}: {type(e).__name__} - {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@stores_bp.route('/<int:store_id>', methods=['GET'])
@jwt_required()
@role_required([UserRole.MERCHANT, UserRole.ADMIN])
def get_store_details(store_id):
    """
    Get detailed information about a specific store including:
    - Basic info
    - Recent sales summary
    - Inventory status
    - Financial overview
    - Top selling products
    - Spoilage data
    - Chart data for sales and spoilage
    Query Parameters:
        - period (str, optional): Reporting period ('weekly', 'monthly', 'annual')
    Responses:
        - 200: Store details
        - 403: Unauthorized access to store
        - 404: User or store not found
        - 500: Internal server error
    """
    try:
        identity = get_jwt_identity()
        current_user_id = identity['id']
        current_user_role = identity['role']
        logger.info(f"Fetching details for store ID {store_id} by user ID: {current_user_id}, role: {current_user_role}")

        current_user = db.session.get(User, current_user_id)
        if not current_user:
            logger.error(f"User not found: {current_user_id}")
            return jsonify({'status': 'error', 'message': 'User not found'}), 404

        store = db.session.get(Store, store_id)
        if not store:
            logger.warning(f"Store ID {store_id} not found")
            return jsonify({'status': 'error', 'message': 'Store not found'}), 404

        has_access = db.session.query(user_store).filter(
            user_store.c.user_id == current_user_id,
            user_store.c.store_id == store_id
        ).first()
        if not has_access:
            logger.warning(f"Unauthorized access to store ID {store_id} by user ID: {current_user_id}")
            return jsonify({'status': 'error', 'message': 'Unauthorized access to store'}), 403

        period = request.args.get('period', 'weekly')
        start_date, end_date = get_period_dates(period)

        sales_data = db.session.query(
            func.sum(SalesRecord.quantity_sold).label('total_quantity'),
            func.sum(SalesRecord.revenue).label('total_revenue')
        ).filter(
            SalesRecord.store_id == store_id,
            SalesRecord.sale_date.between(start_date, end_date)
        ).first()

        sales_chart_query = db.session.query(
            func.date_trunc(period, SalesRecord.sale_date).label('date'),
            func.sum(SalesRecord.revenue).label('revenue')
        ).filter(
            SalesRecord.store_id == store_id,
            SalesRecord.sale_date.between(start_date, end_date)
        ).group_by(
            func.date_trunc(period, SalesRecord.sale_date)
        ).order_by('date')

        sales_chart_data = sales_chart_query.all()
        sales_labels = [row.date.strftime('%Y-%m-%d') for row in sales_chart_data]
        sales_values = [float(row.revenue or 0) for row in sales_chart_data]

        inventory_status = db.session.query(
            func.count(Product.id).label('total_products'),
            func.sum(case(
                [(Product.current_stock <= Product.min_stock_level, 1)],
                else_=0
            )).label('low_stock_items'),
            func.sum(case(
                [(Product.current_stock > Product.min_stock_level, 1)],
                else_=0
            )).label('non_low_stock_items')
        ).filter(Product.store_id == store_id).first()

        financial_data = db.session.query(
            func.sum(case(
                [(InventoryEntry.payment_status == PaymentStatus.PAID, InventoryEntry.buying_price * InventoryEntry.quantity_received)],
                else_=0
            )).label('total_paid'),
            func.sum(case(
                [(InventoryEntry.payment_status == PaymentStatus.UNPAID, InventoryEntry.buying_price * InventoryEntry.quantity_received)],
                else_=0
            )).label('total_unpaid')
        ).filter(
            InventoryEntry.store_id == store_id,
            InventoryEntry.entry_date.between(start_date, end_date)
        ).first()

        top_products = (
            db.session.query(
                Product.name,
                func.sum(SalesRecord.quantity_sold).label('units_sold'),
                func.sum(SalesRecord.revenue).label('revenue')
            )
            .join(SalesRecord, SalesRecord.product_id == Product.id)
            .filter(
                SalesRecord.store_id == store_id,
                SalesRecord.sale_date.between(start_date, end_date)
            )
            .group_by(Product.name)
            .order_by(func.sum(SalesRecord.revenue).desc())
            .limit(5)
            .all()
        )

        spoilage_data = db.session.query(
            func.sum(InventoryEntry.quantity_spoiled).label('total_spoilage')
        ).filter(
            InventoryEntry.store_id == store_id,
            InventoryEntry.entry_date.between(start_date, end_date)
        ).first()

        spoilage_chart_query = db.session.query(
            func.date_trunc(period, InventoryEntry.entry_date).label('date'),
            func.sum(InventoryEntry.quantity_spoiled).label('spoilage')
        ).filter(
            InventoryEntry.store_id == store_id,
            InventoryEntry.entry_date.between(start_date, end_date)
        ).group_by(
            func.date_trunc(period, InventoryEntry.entry_date)
        ).order_by('date')

        spoilage_chart_data = spoilage_chart_query.all()
        spoilage_labels = [row.date.strftime('%Y-%m-%d') for row in spoilage_chart_data]
        spoilage_values = [int(row.spoilage or 0) for row in spoilage_chart_data]

        total_sales = sales_data.total_revenue or 0
        total_spoilage_value = sum(InventoryEntry.quantity_spoiled * InventoryEntry.selling_price
            for entry in db.session.query(InventoryEntry)
            .filter(InventoryEntry.store_id == store_id, InventoryEntry.entry_date.between(start_date, end_date))
            .all()) or 0
        if total_spoilage_value > total_sales * 0.5:
            logger.warning(f"Spoilage value ({total_spoilage_value}) exceeds 50% of sales ({total_sales}) for store ID {store_id}")

        store_data = StoreDetailSchema().dump(store)
        store_data.update({
            'sales_summary': {
                'period': period,
                'total_quantity': int(sales_data.total_quantity or 0),
                'total_revenue': float(sales_data.total_revenue or 0),
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'chart_data': {
                    'labels': sales_labels,
                    'datasets': [{
                        'label': 'Sales Revenue',
                        'data': sales_values
                    }]
                }
            },
            'inventory_status': {
                'total_products': int(inventory_status.total_products or 0),
                'low_stock_items': int(inventory_status.low_stock_items or 0),
                'non_low_stock_items': int(inventory_status.non_low_stock_items or 0)
            },
            'financial_overview': {
                'total_paid': float(financial_data.total_paid or 0),
                'total_unpaid': float(financial_data.total_unpaid or 0)
            },
            'top_products': [
                {
                    'name': product.name,
                    'units_sold': int(product.units_sold or 0),
                    'revenue': float(product.revenue or 0)
                } for product in top_products
            ],
            'spoilage_summary': {
                'total_spoilage': int(spoilage_data.total_spoilage or 0),
                'chart_data': {
                    'labels': spoilage_labels,
                    'datasets': [{
                        'label': 'Spoilage Units',
                        'data': spoilage_values
                    }]
                }
            }
        })

        logger.info(f"Retrieved details for store ID {store_id} by user ID: {current_user_id}")
        return jsonify({'status': 'success', 'store': store_data}), 200

    except Exception as e:
        logger.error(f"Error fetching store details for store ID {store_id} by user ID {current_user_id}: {type(e).__name__} - {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@stores_bp.route('', methods=['POST'])
@jwt_required()
@role_required([UserRole.ADMIN])
def create_store():
    """
    Create a new store (admin only).
    Body:
        - name (str): Store name
        - location (str): Store location
        - description (str, optional): Store description
        - address (str, optional): Store address
    Responses:
        - 201: Store created successfully
        - 400: Missing required fields or store name exists
        - 404: User not found
        - 500: Internal server error
    """
    try:
        identity = get_jwt_identity()
        current_user_id = identity['id']
        current_user_role = identity['role']
        logger.info(f"Creating store by user ID: {current_user_id}, role: {current_user_role}")

        current_user = db.session.get(User, current_user_id)
        if not current_user:
            logger.error(f"User not found: {current_user_id}")
            return jsonify({'status': 'error', 'message': 'User not found'}), 404

        data = request.get_json()
        if not data or not all(k in data for k in ('name', 'location')):
            logger.error(f"Missing required fields in store creation by user ID: {current_user_id}")
            return jsonify({'status': 'error', 'message': 'Missing required fields (name, location)'}), 400

        existing_store = db.session.query(Store).filter(Store.name.ilike(data['name'])).first()
        if existing_store:
            logger.warning(f"Store creation failed: Store name '{data['name']}' already exists")
            return jsonify({'status': 'error', 'message': 'Store name already exists'}), 400

        new_store = Store(
            name=data['name'],
            location=data['location'],
            address=data.get('address', ''),
            description=data.get('description', '')
        )
        db.session.add(new_store)
        db.session.flush()

        db.session.execute(
            user_store.insert().values(user_id=current_user_id, store_id=new_store.id)
        )
        db.session.commit()

        logger.info(f"Store created with ID {new_store.id} by user ID: {current_user_id}")
        return jsonify({
            'status': 'success',
            'message': 'Store created successfully',
            'store': StoreSchema().dump(new_store)
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating store by user ID {current_user_id}: {type(e).__name__} - {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@stores_bp.route('/<int:store_id>', methods=['PUT'])
@jwt_required()
@role_required([UserRole.ADMIN])
def update_store(store_id):
    """
    Update an existing store (admin only).
    Body:
        - name (str, optional): Store name
        - location (str, optional): Store location
        - description (str, optional): Store description
        - address (str, optional): Store address
    Responses:
        - 200: Store updated successfully
        - 400: No data provided or store name exists
        - 403: Unauthorized access to store
        - 404: User or store not found
        - 500: Internal server error
    """
    try:
        identity = get_jwt_identity()
        current_user_id = identity['id']
        current_user_role = identity['role']
        logger.info(f"Updating store ID {store_id} by user ID: {current_user_id}, role: {current_user_role}")

        current_user = db.session.get(User, current_user_id)
        if not current_user:
            logger.error(f"User not found: {current_user_id}")
            return jsonify({'status': 'error', 'message': 'User not found'}), 404

        store = db.session.get(Store, store_id)
        if not store:
            logger.warning(f"Store ID {store_id} not found")
            return jsonify({'status': 'error', 'message': 'Store not found'}), 404

        has_access = db.session.query(user_store).filter(
            user_store.c.user_id == current_user_id,
            user_store.c.store_id == store_id
        ).first()
        if not has_access:
            logger.warning(f"Unauthorized access to store ID {store_id} by user ID: {current_user_id}")
            return jsonify({'status': 'error', 'message': 'Unauthorized access to store'}), 403

        data = request.get_json()
        if not data:
            logger.error(f"No data provided for store update by user ID: {current_user_id}")
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400

        if 'name' in data:
            existing_store = db.session.query(Store).filter(
                Store.name.ilike(data['name']),
                Store.id != store_id
            ).first()
            if existing_store:
                logger.warning(f"Store update failed: Store name '{data['name']}' already exists")
                return jsonify({'status': 'error', 'message': 'Store name already exists'}), 400
            store.name = data['name']
        if 'location' in data:
            store.location = data['location']
        if 'description' in data:
            store.description = data['description']
        if 'address' in data:
            store.address = data['address']

        db.session.commit()
        logger.info(f"Store ID {store_id} updated by user ID: {current_user_id}")
        return jsonify({
            'status': 'success',
            'message': 'Store updated successfully',
            'store': StoreSchema().dump(store)
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating store ID {store_id} by user ID {current_user_id}: {type(e).__name__} - {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@stores_bp.route('/<int:store_id>', methods=['DELETE'])
@jwt_required()
@role_required([UserRole.ADMIN])
def delete_store(store_id):
    """
    Delete a store (admin only).
    Responses:
        - 200: Store deleted successfully
        - 403: Unauthorized access to store
        - 404: User or store not found
        - 500: Internal server error
    """
    try:
        identity = get_jwt_identity()
        current_user_id = identity['id']
        current_user_role = identity['role']
        logger.info(f"Deleting store ID {store_id} by user ID: {current_user_id}, role: {current_user_role}")

        current_user = db.session.get(User, current_user_id)
        if not current_user:
            logger.error(f"User not found: {current_user_id}")
            return jsonify({'status': 'error', 'message': 'User not found'}), 404

        store = db.session.get(Store, store_id)
        if not store:
            logger.warning(f"Store ID {store_id} not found")
            return jsonify({'status': 'error', 'message': 'Store not found'}), 404

        has_access = db.session.query(user_store).filter(
            user_store.c.user_id == current_user_id,
            user_store.c.store_id == store_id
        ).first()
        if not has_access:
            logger.warning(f"Unauthorized access to store ID {store_id} by user ID: {current_user_id}")
            return jsonify({'status': 'error', 'message': 'Unauthorized access to store'}), 403

        db.session.execute(
            user_store.delete().where(user_store.c.store_id == store_id)
        )
        db.session.delete(store)
        db.session.commit()

        logger.info(f"Store ID {store_id} deleted by user ID: {current_user_id}")
        return jsonify({
            'status': 'success',
            'message': 'Store deleted successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting store ID {store_id} by user ID {current_user_id}: {type(e).__name__} - {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500