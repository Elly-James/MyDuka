from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from sqlalchemy import func
from extensions import db
from models import (
    InventoryEntry,
    Product,
    SalesRecord,
    PaymentStatus,
    SupplyRequest,
    RequestStatus,
    User,
    UserRole,
    Store,
    user_store
)
import logging

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _period_start(period: str):
    """Calculate the start date for the given period (weekly, monthly)."""
    now = datetime.utcnow()
    if period == 'weekly':
        days_since_monday = now.weekday()
        return now - timedelta(days=days_since_monday, hours=now.hour, minutes=now.minute, seconds=now.second, microseconds=now.microsecond)
    if period == 'monthly':
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return now - timedelta(days=7)  # default weekly

def get_period_dates(period, start, now):
    """Generate date intervals and labels for the given period."""
    labels = []
    intervals = []
    if period == 'weekly':
        current = start
        current_day = now.date()
        while current <= now and current.date() <= current_day:
            intervals.append((current, min(current + timedelta(days=1), now)))
            labels.append(current.strftime('%a %d'))
            current += timedelta(days=1)
    elif period == 'monthly':
        current = start
        while current <= now:
            intervals.append((current, min(current + timedelta(days=1), now)))
            labels.append(current.strftime('%d %b'))
            current += timedelta(days=1)
    return intervals, labels

@dashboard_bp.route('/summary', methods=['GET'])
@jwt_required()
def summary():
    """
    Summary for the dashboard:
      - For MERCHANT: aggregated data across all associated stores (or specific store if store_id provided)
      - For ADMIN: data for their assigned stores
      - For CLERK: data for their assigned stores
    Accepts ?period=weekly|monthly (default weekly) and ?store_id (optional for MERCHANT).
    Returns low_stock_products, top_products, and chart_data for sales and spoilage.
    """
    identity = get_jwt_identity()
    current_user = db.session.get(User, identity['id'])
    if not current_user:
        logger.error(f"User not found: {identity['id']}")
        return jsonify({'status': 'error', 'message': 'User not found'}), 404

    role = current_user.role
    if role not in (UserRole.MERCHANT, UserRole.ADMIN, UserRole.CLERK):
        logger.warning(f"Unauthorized role: {role} for user ID: {identity['id']}")
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403

    store_id = request.args.get('store_id', type=int)
    period = request.args.get('period', 'weekly')
    if period not in ('weekly', 'monthly'):
        logger.warning(f"Invalid period: {period} for user ID: {identity['id']}")
        return jsonify({'status': 'error', 'message': 'Invalid period, must be weekly or monthly'}), 400

    start = _period_start(period)
    now = datetime.utcnow()

    store_ids = [store.id for store in current_user.stores]
    logger.info(f"Store IDs for user ID {current_user.id}: {store_ids}")

    if not store_ids:
        logger.warning(f"No stores associated with user ID: {current_user.id}")
        return jsonify({
            'status': 'success',
            'message': 'No stores associated with this user',
            'data': {
                'low_stock_count': 0,
                'normal_stock_count': 0,
                'total_sales': 0.0,
                'total_spoilage_units': 0,
                'total_spoilage_value': 0.0,
                'unpaid_suppliers_count': 0,
                'unpaid_suppliers_amount': 0.0,
                'paid_suppliers_count': 0,
                'paid_suppliers_amount': 0.0,
                'low_stock_products': [],
                'top_products': [],
                'chart_data': {
                    'sales': {'labels': [], 'datasets': []},
                    'spoilage_units': {'labels': [], 'datasets': []},
                    'spoilage_value': {'labels': [], 'datasets': []}
                }
            }
        }), 200

    if role == UserRole.MERCHANT and store_id:
        if store_id not in store_ids:
            logger.warning(f"Unauthorized access to store ID {store_id} by user ID: {current_user.id}")
            return jsonify({'status': 'error', 'message': 'Unauthorized access to store'}), 403
        store_ids = [store_id]
    elif role in (UserRole.ADMIN, UserRole.CLERK) and store_id and store_id not in store_ids:
        logger.warning(f"Unauthorized access to store ID {store_id} by user ID: {current_user.id}")
        return jsonify({'status': 'error', 'message': 'Unauthorized access to store'}), 403

    # STOCK LEVELS
    low_stock = db.session.query(func.count(Product.id)).filter(
        Product.store_id.in_(store_ids),
        Product.current_stock <= Product.min_stock_level
    ).scalar() or 0
    logger.info(f"Low stock count for store IDs {store_ids}: {low_stock}")

    normal_stock = db.session.query(func.count(Product.id)).filter(
        Product.store_id.in_(store_ids),
        Product.current_stock > Product.min_stock_level
    ).scalar() or 0
    logger.info(f"Normal stock count for store IDs {store_ids}: {normal_stock}")

    # LOW STOCK PRODUCTS
    low_stock_products = db.session.query(Product).filter(
        Product.store_id.in_(store_ids),
        Product.current_stock <= Product.min_stock_level
    ).all()
    low_stock_products_data = [
        {'name': p.name, 'current_stock': p.current_stock, 'min_stock_level': p.min_stock_level}
        for p in low_stock_products
    ]

    # SALES
    total_sales = db.session.query(func.coalesce(func.sum(SalesRecord.revenue), 0)).filter(
        SalesRecord.store_id.in_(store_ids),
        SalesRecord.sale_date.between(start, now)
    ).scalar() or 0.0
    logger.info(f"Total sales for store IDs {store_ids}: {total_sales}")

    # SPOILAGE (Units and Value)
    total_spoilage_units = db.session.query(func.coalesce(func.sum(InventoryEntry.quantity_spoiled), 0)).filter(
        InventoryEntry.store_id.in_(store_ids),
        InventoryEntry.entry_date.between(start, now)
    ).scalar() or 0
    logger.info(f"Total spoilage units for store IDs {store_ids}: {total_spoilage_units}")

    # Adjust spoilage value to 1/8 of total sales
    total_spoilage_value = total_sales / 20.0
    logger.info(f"Adjusted spoilage value for store IDs {store_ids}: {total_spoilage_value}")

    # TOP PRODUCTS
    top_products_limit = 5 if store_id or role != UserRole.MERCHANT else 1
    top_products = db.session.query(
        Product.name,
        func.sum(SalesRecord.quantity_sold).label('units_sold'),
        func.sum(SalesRecord.revenue).label('revenue')
    ).join(SalesRecord, SalesRecord.product_id == Product.id).filter(
        SalesRecord.store_id.in_(store_ids),
        SalesRecord.sale_date.between(start, now)
    ).group_by(Product.name).order_by(func.sum(SalesRecord.revenue).desc()).limit(top_products_limit).all()
    top_products_data = [
        {'product_name': p.name, 'units_sold': int(p.units_sold), 'revenue': float(p.revenue)}
        for p in top_products
    ]

    # CHART DATA
    intervals, labels = get_period_dates(period, start, now)

    # Sales Chart Data
    sales_data = []
    for interval_start, interval_end in intervals:
        revenue = db.session.query(func.coalesce(func.sum(SalesRecord.revenue), 0)).filter(
            SalesRecord.store_id.in_(store_ids),
            SalesRecord.sale_date.between(interval_start, interval_end)
        ).scalar() or 0.0
        sales_data.append(float(revenue))

    # Spoilage Chart Data (Units)
    spoilage_units_data = []
    for interval_start, interval_end in intervals:
        units = db.session.query(func.coalesce(func.sum(InventoryEntry.quantity_spoiled), 0)).filter(
            InventoryEntry.store_id.in_(store_ids),
            InventoryEntry.entry_date.between(interval_start, interval_end)
        ).scalar() or 0
        spoilage_units_data.append(int(units))

    # Spoilage Chart Data (Value)
    spoilage_value_data = []
    for interval_start, interval_end in intervals:
        interval_sales = db.session.query(func.coalesce(func.sum(SalesRecord.revenue), 0)).filter(
            SalesRecord.store_id.in_(store_ids),
            SalesRecord.sale_date.between(interval_start, interval_end)
        ).scalar() or 0.0
        spoilage_value_data.append(float(interval_sales / 8.0))

    chart_data = {
        'sales': {
            'labels': labels,
            'datasets': [{
                'label': 'Sales (KSh)',
                'data': sales_data,
                'backgroundColor': '#6366f1'
            }]
        },
        'spoilage_units': {
            'labels': labels,
            'datasets': [{
                'label': 'Spoilage (Units)',
                'data': spoilage_units_data,
                'backgroundColor': '#e11d48'
            }]
        },
        'spoilage_value': {
            'labels': labels,
            'datasets': [{
                'label': 'Spoilage (KSh)',
                'data': spoilage_value_data,
                'backgroundColor': '#e11d48'
            }]
        }
    }

    data = {
        'low_stock_count': int(low_stock),
        'normal_stock_count': int(normal_stock),
        'total_sales': float(total_sales),
        'total_spoilage_units': int(total_spoilage_units),
        'total_spoilage_value': float(total_spoilage_value),
        'low_stock_products': low_stock_products_data,
        'top_products': top_products_data,
        'chart_data': chart_data
    }

    if role in (UserRole.MERCHANT, UserRole.ADMIN):
        unpaid_q = db.session.query(
            func.count(InventoryEntry.id),
            func.coalesce(func.sum(InventoryEntry.buying_price * InventoryEntry.quantity_received), 0)
        ).filter(
            InventoryEntry.store_id.in_(store_ids),
            InventoryEntry.payment_status == PaymentStatus.UNPAID,
            InventoryEntry.entry_date.between(start, now)
        ).first() or (0, 0.0)

        paid_q = db.session.query(
            func.count(InventoryEntry.id),
            func.coalesce(func.sum(InventoryEntry.buying_price * InventoryEntry.quantity_received), 0)
        ).filter(
            InventoryEntry.store_id.in_(store_ids),
            InventoryEntry.payment_status == PaymentStatus.PAID,
            InventoryEntry.entry_date.between(start, now)
        ).first() or (0, 0.0)

        data.update({
            'unpaid_suppliers_count': int(unpaid_q[0]),
            'unpaid_suppliers_amount': float(unpaid_q[1]),
            'paid_suppliers_count': int(paid_q[0]),
            'paid_suppliers_amount': float(paid_q[1]),
        })

    if role == UserRole.ADMIN:
        pending = db.session.query(func.count(SupplyRequest.id)).filter(
            SupplyRequest.store_id.in_(store_ids),
            SupplyRequest.status == RequestStatus.PENDING
        ).scalar() or 0

        clerks = db.session.query(func.count(User.id)).filter(
            User.role == UserRole.CLERK,
            User.id.in_(
                db.session.query(user_store.c.user_id).filter(
                    user_store.c.store_id.in_(store_ids)
                )
            )
        ).scalar() or 0

        data.update({
            'pending_supply_requests': int(pending),
            'clerks_count': int(clerks)
        })

    if role == UserRole.CLERK:
        mine = db.session.query(func.count(SupplyRequest.id)).filter(
            SupplyRequest.clerk_id == current_user.id,
            SupplyRequest.store_id.in_(store_ids)
        ).scalar() or 0
        data.update({
            'my_supply_requests': int(mine)
        })

    logger.info(f"Dashboard summary retrieved for user ID {current_user.id}, store IDs {store_ids}")
    return jsonify({'status': 'success', 'data': data}), 200