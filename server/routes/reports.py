from flask import Blueprint, jsonify, request, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db, cache
from models import SalesRecord, InventoryEntry, Product, Supplier, User, UserRole, Store, PaymentStatus, ProductCategory, user_store
from schemas import SalesReportSchema, SpoilageReportSchema, PaymentStatusReportSchema
from sqlalchemy import func
from datetime import datetime, timedelta
import logging
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import openpyxl
from io import BytesIO
from functools import wraps

reports_bp = Blueprint('reports', __name__, url_prefix='/api/reports')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def role_required(roles):
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

def get_period_dates(period):
    """Calculate start and end dates for the given period (weekly, monthly)."""
    today = datetime.utcnow().replace(hour=23, minute=59, second=59, microsecond=999999)
    if period == 'weekly':
        start = today - timedelta(days=7)
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = today
    elif period == 'monthly':
        start = datetime(2025, 1, 1)
        end = datetime(2025, 5, 31, 23, 59, 59, 999999)
    else:
        start = today - timedelta(days=7)
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = today
    return start, end

def get_previous_period_dates(period, end_date):
    """Calculate start and end dates for the previous period."""
    if period == 'weekly':
        start = end_date - timedelta(days=14)
        end = end_date - timedelta(days=7)
    elif period == 'monthly':
        start = (end_date.replace(day=1) - timedelta(days=1)).replace(day=1)
        end = (start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
    else:
        start = end_date - timedelta(days=7)
        end = end_date
    return start, end

def get_store_ids(user_id, role, store_id=None):
    """Get accessible store IDs for the user based on their role."""
    user = db.session.get(User, user_id)
    if not user:
        return []
    
    store_ids = [store.id for store in user.stores]
    
    if role == UserRole.MERCHANT:
        if store_id and store_id in store_ids:
            return [store_id]
        return store_ids
    else:
        if store_id and store_id not in store_ids:
            return []
        return store_ids

@reports_bp.route('/sales', methods=['GET'])
@jwt_required()
@role_required([UserRole.MERCHANT, UserRole.ADMIN])
@cache.cached(timeout=300, key_prefix=lambda: f"sales_{get_jwt_identity()['id']}_{request.full_path}")
def get_sales_report():
    """Fetch sales report with total quantity, revenue, and chart data for line graph."""
    try:
        identity = get_jwt_identity()
        current_user_id = identity['id']
        current_user_role = identity['role']
        logger.info(f"Fetching sales report for user ID: {current_user_id}, role: {current_user_role}")

        period = request.args.get('period', 'weekly')
        store_id = request.args.get('store_id', type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        if period not in ['weekly', 'monthly']:
            logger.error(f"Invalid period provided: {period}")
            return jsonify({'status': 'error', 'message': 'Invalid period. Use weekly or monthly'}), 400

        if start_date and end_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d')
                if start > end:
                    logger.error("Start date is after end date")
                    return jsonify({'status': 'error', 'message': 'Start date must be before end date'}), 400
            except ValueError:
                logger.error(f"Invalid date format: start_date={start_date}, end_date={end_date}")
                return jsonify({'status': 'error', 'message': 'Invalid date format. Use YYYY-MM-DD'}), 400
        else:
            start, end = get_period_dates(period)

        store_ids = get_store_ids(current_user_id, current_user_role, store_id)
        if not store_ids:
            logger.warning(f"No accessible stores for user ID: {current_user_id}")
            return jsonify({
                'status': 'success',
                'message': 'No accessible stores for this user',
                'data': {
                    'total_quantity_sold': 0,
                    'total_revenue': 0.0,
                    'chart_data': {
                        'labels': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] if period == 'weekly' else ['Jan', 'Feb', 'Mar', 'Apr', 'May'],
                        'datasets': [{'label': 'Sales (KSh)', 'data': [0] * (7 if period == 'weekly' else 5), 'backgroundColor': '#6366f1', 'borderColor': '#6366f1'}]
                    }
                }
            }), 200

        # Sales data
        query = (
            db.session.query(SalesRecord)
            .filter(
                SalesRecord.store_id.in_(store_ids),
                SalesRecord.sale_date.between(start, end)
            )
        )
        sales_data = query.with_entities(
            func.sum(SalesRecord.quantity_sold).label('total_quantity'),
            func.sum(SalesRecord.revenue).label('total_revenue')
        ).first()

        # Chart data
        labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] if period == 'weekly' else ['Jan', 'Feb', 'Mar', 'Apr', 'May']
        sales_data_chart = [0] * len(labels)
        for i, _ in enumerate(labels):
            interval_start = start + timedelta(days=i) if period == 'weekly' else datetime(2025, i + 1, 1)
            interval_end = interval_start + (timedelta(days=1) if period == 'weekly' else timedelta(days=31))
            interval_end = min(interval_end, end)
            revenue = db.session.query(func.coalesce(func.sum(SalesRecord.revenue), 0)).filter(
                SalesRecord.store_id.in_(store_ids),
                SalesRecord.sale_date.between(interval_start, interval_end)
            ).scalar() or 0.0
            sales_data_chart[i] = float(revenue)

        report_data = {
            'total_quantity_sold': int(sales_data.total_quantity or 0),
            'total_revenue': float(sales_data.total_revenue or 0),
            'chart_data': {
                'labels': labels,
                'datasets': [{
                    'label': 'Sales (KSh)',
                    'data': sales_data_chart,
                    'backgroundColor': '#6366f1',
                    'borderColor': '#6366f1'
                }]
            }
        }

        logger.info(f"Sales report retrieved for user ID: {current_user_id}, store IDs: {store_ids}")
        return jsonify({'status': 'success', 'data': SalesReportSchema().dump(report_data)}), 200

    except Exception as e:
        logger.error(f"Error fetching sales report for user ID {current_user_id}: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@reports_bp.route('/spoilage', methods=['GET'])
@jwt_required()
@role_required([UserRole.MERCHANT, UserRole.ADMIN])
@cache.cached(timeout=300, key_prefix=lambda: f"spoilage_{get_jwt_identity()['id']}_{request.full_path}")
def get_spoilage_report():
    """Fetch spoilage report with total value and chart data for pie chart (percentages by category)."""
    try:
        identity = get_jwt_identity()
        current_user_id = identity['id']
        current_user_role = identity['role']
        logger.info(f"Fetching spoilage report for user ID: {current_user_id}, role: {current_user_role}")

        store_id = request.args.get('store_id', type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        period = request.args.get('period', 'weekly')

        if period not in ['weekly', 'monthly']:
            logger.error(f"Invalid period provided: {period}")
            return jsonify({'status': 'error', 'message': 'Invalid period. Use weekly or monthly'}), 400

        if start_date and end_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d')
                if start > end:
                    logger.error("Start date is after end date")
                    return jsonify({'status': 'error', 'message': 'Start date must be before end date'}), 400
            except ValueError:
                logger.error(f"Invalid date format: start_date={start_date}, end_date={end_date}")
                return jsonify({'status': 'error', 'message': 'Invalid date format. Use YYYY-MM-DD'}), 400
        else:
            start, end = get_period_dates(period)

        store_ids = get_store_ids(current_user_id, current_user_role, store_id)
        if not store_ids:
            logger.warning(f"No accessible stores for user ID: {current_user_id}")
            return jsonify({
                'status': 'success',
                'message': 'No accessible stores for this user',
                'data': {
                    'total_spoilage_value': 0.0,
                    'chart_data': {
                        'labels': ['No Data'],
                        'datasets': [{
                            'label': 'Spoilage (%)',
                            'data': [0],
                            'backgroundColor': ['#e11d48'],
                            'borderColor': ['#e11d48']
                        }]
                    }
                }
            }), 200

        # Spoilage data
        query = (
            db.session.query(InventoryEntry)
            .join(Product, Product.id == InventoryEntry.product_id)
            .filter(
                InventoryEntry.store_id.in_(store_ids),
                InventoryEntry.entry_date.between(start, end),
                InventoryEntry.spoilage_quantity > 0
            )
        )
        total_spoilage_value = query.with_entities(
            func.sum(InventoryEntry.spoilage_quantity * InventoryEntry.buying_price)
        ).scalar() or 0.0

        # Category data for pie chart
        categories = (
            query.join(ProductCategory, Product.category_id == ProductCategory.id)
            .group_by(ProductCategory.name)
            .with_entities(
                ProductCategory.name.label('category_name'),
                func.sum(InventoryEntry.spoilage_quantity).label('spoilage_quantity')
            )
            .all()
        )
        total_spoilage_quantity = sum(cat.spoilage_quantity for cat in categories) or 1
        labels = [cat.category_name for cat in categories] or ['No Data']
        percentages = [(cat.spoilage_quantity / total_spoilage_quantity * 100) if total_spoilage_quantity > 0 else 0 for cat in categories]
        colors = ['#f43f5e', '#fb7185', '#fecdd3', '#fed7aa', '#f97316'][:len(labels)] or ['#e11d48']

        report_data = {
            'total_spoilage_value': float(total_spoilage_value),
            'chart_data': {
                'labels': labels,
                'datasets': [{
                    'label': 'Spoilage (%)',
                    'data': percentages,
                    'backgroundColor': colors,
                    'borderColor': colors
                }]
            }
        }

        logger.info(f"Spoilage report retrieved for user ID: {current_user_id}, store IDs: {store_ids}, total_spoilage_value: {report_data['total_spoilage_value']}")
        return jsonify({'status': 'success', 'data': SpoilageReportSchema().dump(report_data)}), 200

    except Exception as e:
        logger.error(f"Error fetching spoilage report for user ID {current_user_id}: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@reports_bp.route('/payment-status', methods=['GET'])
@jwt_required()
@role_required([UserRole.MERCHANT, UserRole.ADMIN])
@cache.cached(timeout=300, key_prefix=lambda: f"payment_status_{get_jwt_identity()['id']}_{request.full_path}")
def get_payment_status_report():
    """Fetch payment status report with paid/unpaid amounts and supplier data."""
    try:
        identity = get_jwt_identity()
        current_user_id = identity['id']
        current_user_role = identity['role']
        logger.info(f"Fetching payment status report for user ID: {current_user_id}, role: {current_user_role}")

        store_id = request.args.get('store_id', type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        period = request.args.get('period', 'monthly')

        if period != 'monthly':
            logger.error(f"Invalid period provided: {period}")
            return jsonify({'status': 'error', 'message': 'Invalid period. Use monthly'}), 400

        if start_date and end_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d')
                if start > end:
                    logger.error("Start date is after end date")
                    return jsonify({'status': 'error', 'message': 'Start date must be before end date'}), 400
            except ValueError:
                logger.error(f"Invalid date format: start_date={start_date}, end_date={end_date}")
                return jsonify({'status': 'error', 'message': 'Invalid date format. Use YYYY-MM-DD'}), 400
        else:
            start, end = get_period_dates(period)

        store_ids = get_store_ids(current_user_id, current_user_role, store_id)
        if not store_ids:
            logger.warning(f"No accessible stores for user ID: {current_user_id}")
            return jsonify({
                'status': 'success',
                'message': 'No accessible stores for this user',
                'data': {
                    'total_paid': 0.0,
                    'total_unpaid': 0.0,
                    'suppliers': []
                }
            }), 200

        # Payment data
        payment_data = db.session.query(
            func.coalesce(func.sum(func.case(
                [(InventoryEntry.payment_status == PaymentStatus.PAID, InventoryEntry.buying_price * InventoryEntry.quantity_received)],
                else_=0
            )), 0).label('total_paid'),
            func.coalesce(func.sum(func.case(
                [(InventoryEntry.payment_status == PaymentStatus.UNPAID, InventoryEntry.buying_price * InventoryEntry.quantity_received)],
                else_=0
            )), 0).label('total_unpaid')
        ).filter(
            InventoryEntry.store_id.in_(store_ids),
            InventoryEntry.entry_date.between(start, end)
        ).first()

        # Suppliers data
        suppliers_data = (
            db.session.query(
                Supplier.name,
                func.coalesce(func.sum(func.case(
                    [(InventoryEntry.payment_status == PaymentStatus.PAID, InventoryEntry.buying_price * InventoryEntry.quantity_received)],
                    else_=0
                )), 0).label('paid_amount'),
                func.coalesce(func.sum(func.case(
                    [(InventoryEntry.payment_status == PaymentStatus.UNPAID, InventoryEntry.buying_price * InventoryEntry.quantity_received)],
                    else_=0
                )), 0).label('unpaid_amount')
            )
            .join(InventoryEntry, InventoryEntry.supplier_id == Supplier.id)
            .filter(
                InventoryEntry.store_id.in_(store_ids),
                InventoryEntry.entry_date.between(start, end)
            )
            .group_by(Supplier.name)
            .all()
        )

        report_data = {
            'total_paid': float(payment_data.total_paid or 0),
            'total_unpaid': float(payment_data.total_unpaid or 0),
            'suppliers': [
                {
                    'name': supplier.name,
                    'paid_amount': float(supplier.paid_amount or 0),
                    'unpaid_amount': float(supplier.unpaid_amount or 0)
                } for supplier in suppliers_data
            ]
        }

        logger.info(f"Payment status report retrieved for user ID: {current_user_id}, store IDs: {store_ids}")
        return jsonify({'status': 'success', 'data': PaymentStatusReportSchema().dump(report_data)}), 200

    except Exception as e:
        logger.error(f"Error fetching payment status report for user ID {current_user_id}: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@reports_bp.route('/top-products', methods=['GET'])
@jwt_required()
@role_required([UserRole.MERCHANT, UserRole.ADMIN])
@cache.cached(timeout=300, key_prefix=lambda: f"top_products_{get_jwt_identity()['id']}_{request.full_path}")
def get_top_products():
    """Fetch top products report based on revenue."""
    try:
        identity = get_jwt_identity()
        current_user_id = identity['id']
        current_user_role = identity['role']
        logger.info(f"Fetching top products report for user ID: {current_user_id}, role: {current_user_role}")

        store_id = request.args.get('store_id', type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        period = request.args.get('period', 'weekly')
        limit = request.args.get('limit', 10 if not store_id else 5, type=int)

        if period not in ['weekly', 'monthly']:
            logger.error(f"Invalid period provided: {period}")
            return jsonify({'status': 'error', 'message': 'Invalid period. Use weekly or monthly'}), 400

        if start_date and end_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d')
                if start > end:
                    logger.error("Start date is after end date")
                    return jsonify({'status': 'error', 'message': 'Start date must be before end date'}), 400
            except ValueError:
                logger.error(f"Invalid date format: start_date={start_date}, end_date={end_date}")
                return jsonify({'status': 'error', 'message': 'Invalid date format. Use YYYY-MM-DD'}), 400
        else:
            start, end = get_period_dates(period)

        store_ids = get_store_ids(current_user_id, current_user_role, store_id)
        if not store_ids:
            logger.warning(f"No accessible stores for user ID: {current_user_id}")
            return jsonify({
                'status': 'success',
                'message': 'No accessible stores for this user',
                'top_products': []
            }), 200

        top_products_query = (
            db.session.query(
                Product.name.label('product_name'),
                func.sum(SalesRecord.quantity_sold).label('units_sold'),
                func.sum(SalesRecord.revenue).label('revenue'),
                (func.sum(SalesRecord.revenue) / func.sum(SalesRecord.quantity_sold)).label('unit_price')
            )
            .join(SalesRecord, SalesRecord.product_id == Product.id)
            .filter(
                SalesRecord.store_id.in_(store_ids),
                SalesRecord.sale_date.between(start, end)
            )
            .group_by(Product.name)
            .order_by(func.sum(SalesRecord.revenue).desc())
            .limit(limit)
        )
        top_products = top_products_query.all()

        prev_start, prev_end = get_previous_period_dates(period, end)
        top_products_with_growth = []
        for product in top_products:
            prev_revenue = (
                db.session.query(func.sum(SalesRecord.revenue))
                .join(Product, Product.id == SalesRecord.product_id)
                .filter(
                    SalesRecord.store_id.in_(store_ids),
                    SalesRecord.sale_date.between(prev_start, prev_end),
                    Product.name == product.product_name
                )
                .scalar() or 0
            )
            current_revenue = product.revenue or 0
            growth = (
                ((current_revenue - prev_revenue) / prev_revenue * 100)
                if prev_revenue > 0
                else (100 if current_revenue > 0 else 0)
            )
            top_products_with_growth.append({
                'product_name': product.product_name,
                'units_sold': int(product.units_sold or 0),
                'revenue': float(product.revenue or 0),
                'unit_price': float(product.unit_price or 0) if product.units_sold > 0 else 0.0,
                'growth': round(float(growth), 2) if growth is not None else 0.0
            })

        logger.info(f"Top products report retrieved for user ID: {current_user_id}, store IDs: {store_ids}, count: {len(top_products_with_growth)}")
        return jsonify({
            'status': 'success',
            'top_products': top_products_with_growth
        }), 200

    except Exception as e:
        logger.error(f"Error fetching top products report for user ID {current_user_id}: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@reports_bp.route('/dashboard/summary', methods=['GET'])
@jwt_required()
@role_required([UserRole.MERCHANT, UserRole.ADMIN])
@cache.cached(timeout=300, key_prefix=lambda: f"dashboard_summary_{get_jwt_identity()['id']}_{request.full_path}")
def dashboard_summary():
    """Fetch dashboard summary with stock, sales, spoilage, and supplier payment data."""
    try:
        identity = get_jwt_identity()
        current_user_id = identity['id']
        current_user_role = identity['role']
        logger.info(f"Fetching dashboard summary for user ID: {current_user_id}, role: {current_user_role}")

        store_id = request.args.get('store_id', type=int)
        period = request.args.get('period', 'weekly')

        if period not in ['weekly', 'monthly']:
            logger.error(f"Invalid period provided: {period}")
            return jsonify({'status': 'error', 'message': 'Invalid period. Use weekly or monthly'}), 400

        store_ids = get_store_ids(current_user_id, current_user_role, store_id)
        if not store_ids:
            logger.warning(f"No accessible stores for user ID: {current_user_id}")
            return jsonify({
                'status': 'success',
                'message': 'No accessible stores for this user',
                'data': {
                    'low_stock_count': 0,
                    'low_stock_products': [],
                    'normal_stock_count': 0,
                    'total_sales': 0.0,
                    'total_spoilage_value': 0.0,
                    'spoilage_percentage': 0.0,
                    'unpaid_suppliers_count': 0,
                    'unpaid_suppliers_amount': 0.0,
                    'paid_suppliers_count': 0,
                    'paid_suppliers_amount': 0.0,
                    'paid_percentage': 0.0,
                    'unpaid_percentage': 0.0
                }
            }), 200

        start, end = get_period_dates(period)

        # Stock data
        low_stock_query = (
            db.session.query(
                Product.name,
                Product.current_stock,
                Product.min_stock_level
            )
            .filter(
                Product.store_id.in_(store_ids),
                Product.current_stock <= Product.min_stock_level
            )
        )
        low_stock_products = low_stock_query.all()
        low_stock_count = len(low_stock_products)

        normal_stock_count = (
            db.session.query(func.count(Product.id))
            .filter(
                Product.store_id.in_(store_ids),
                Product.current_stock > Product.min_stock_level
            )
            .scalar() or 0
        )

        # Sales data
        total_sales = (
            db.session.query(func.coalesce(func.sum(SalesRecord.revenue), 0))
            .filter(
                SalesRecord.store_id.in_(store_ids),
                SalesRecord.sale_date.between(start, end)
            )
            .scalar() or 0.0
        )

        # Spoilage data
        spoilage_query = (
            db.session.query(InventoryEntry)
            .filter(
                InventoryEntry.store_id.in_(store_ids),
                InventoryEntry.entry_date.between(start, end),
                InventoryEntry.spoilage_quantity > 0
            )
        )
        total_spoilage = spoilage_query.with_entities(
            func.sum(InventoryEntry.spoilage_quantity * InventoryEntry.buying_price)
        ).scalar() or 0.0
        total_inventory = db.session.query(
            func.sum(InventoryEntry.quantity_received)
        ).filter(
            InventoryEntry.store_id.in_(store_ids),
            InventoryEntry.entry_date.between(start, end)
        ).scalar() or 1
        spoilage_percentage = (total_spoilage / total_inventory) * 100 if total_inventory > 0 else 0

        # Supplier payments
        payment_data = db.session.query(
            func.count(func.case([(InventoryEntry.payment_status == PaymentStatus.PAID, InventoryEntry.id)], else_=None)).label('paid_count'),
            func.coalesce(func.sum(func.case(
                [(InventoryEntry.payment_status == PaymentStatus.PAID, InventoryEntry.buying_price * InventoryEntry.quantity_received)],
                else_=0
            )), 0).label('paid_amount'),
            func.count(func.case([(InventoryEntry.payment_status == PaymentStatus.UNPAID, InventoryEntry.id)], else_=None)).label('unpaid_count'),
            func.coalesce(func.sum(func.case(
                [(InventoryEntry.payment_status == PaymentStatus.UNPAID, InventoryEntry.buying_price * InventoryEntry.quantity_received)],
                else_=0
            )), 0).label('unpaid_amount')
        ).filter(
            InventoryEntry.store_id.in_(store_ids),
            InventoryEntry.entry_date.between(start, end)
        ).first()

        total_payment = payment_data.paid_amount + payment_data.unpaid_amount
        paid_percentage = (payment_data.paid_amount / total_payment * 100) if total_payment > 0 else 0
        unpaid_percentage = (payment_data.unpaid_amount / total_payment * 100) if total_payment > 0 else 0

        data = {
            'low_stock_count': int(low_stock_count),
            'low_stock_products': [
                {
                    'name': row.name,
                    'current_stock': int(row.current_stock or 0),
                    'min_stock_level': int(row.min_stock_level or 0)
                } for row in low_stock_products
            ],
            'normal_stock_count': int(normal_stock_count),
            'total_sales': float(total_sales),
            'total_spoilage_value': float(total_spoilage),
            'spoilage_percentage': round(spoilage_percentage, 2),
            'unpaid_suppliers_count': int(payment_data.unpaid_count or 0),
            'unpaid_suppliers_amount': float(payment_data.unpaid_amount or 0),
            'paid_suppliers_count': int(payment_data.paid_count or 0),
            'paid_suppliers_amount': float(payment_data.paid_amount or 0),
            'paid_percentage': round(paid_percentage, 2),
            'unpaid_percentage': round(unpaid_percentage, 2)
        }

        logger.info(f"Dashboard summary retrieved for user ID: {current_user_id}, store IDs: {store_ids}")
        return jsonify({'status': 'success', 'data': data}), 200

    except Exception as e:
        logger.error(f"Error fetching dashboard summary for user ID {current_user_id}: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@reports_bp.route('/store-comparison', methods=['GET'])
@jwt_required()
@role_required([UserRole.MERCHANT])
@cache.cached(timeout=300, key_prefix=lambda: f"store_comparison_{get_jwt_identity()['id']}_{request.full_path}")
def store_comparison():
    """Fetch store comparison report for revenue and spoilage."""
    try:
        identity = get_jwt_identity()
        current_user_id = identity['id']
        logger.info(f"Fetching store comparison report for user ID: {current_user_id}")

        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        period = request.args.get('period', 'weekly')

        if period not in ['weekly', 'monthly']:
            logger.error(f"Invalid period provided: {period}")
            return jsonify({'status': 'error', 'message': 'Invalid period. Use weekly or monthly'}), 400

        if start_date and end_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d')
                if start > end:
                    logger.error("Start date is after end date")
                    return jsonify({'status': 'error', 'message': 'Start date must be before end date'}), 400
            except ValueError:
                logger.error(f"Invalid date format: start_date={start_date}, end_date={end_date}")
                return jsonify({'status': 'error', 'message': 'Invalid date format. Use YYYY-MM-DD'}), 400
        else:
            start, end = get_period_dates(period)

        store_ids = get_store_ids(current_user_id, UserRole.MERCHANT)
        if not store_ids:
            logger.warning(f"No accessible stores for user ID: {current_user_id}")
            return jsonify({
                'status': 'success',
                'message': 'No accessible stores for this user',
                'report': {'chart_data': {'labels': ['Revenue', 'Spoilage'], 'datasets': []}}
            }), 200

        stores = db.session.query(Store).filter(Store.id.in_(store_ids)).all()
        datasets = []
        for store in stores:
            sales = (
                db.session.query(func.coalesce(func.sum(SalesRecord.revenue), 0))
                .filter(
                    SalesRecord.store_id == store.id,
                    SalesRecord.sale_date.between(start, end)
                )
                .scalar() or 0.0
            )
            spoilage = (
                db.session.query(
                    func.coalesce(func.sum(InventoryEntry.spoilage_quantity * InventoryEntry.buying_price), 0)
                )
                .filter(
                    InventoryEntry.store_id == store.id,
                    InventoryEntry.entry_date.between(start, end),
                    InventoryEntry.spoilage_quantity > 0
                )
                .scalar() or 0.0
            )
            datasets.append({
                'label': store.name,
                'data': [float(sales), float(spoilage)],
                'backgroundColor': f'#{hash(store.name) % 0xFFFFFF:06x}',
                'borderColor': f'#{hash(store.name) % 0xFFFFFF:06x}'
            })

        chart_data = {
            'labels': ['Revenue (KSh)', 'Spoilage (KSh)'],
            'datasets': datasets
        }

        report_data = {'chart_data': chart_data}
        logger.info(f"Store comparison report retrieved for user ID: {current_user_id}, store IDs: {store_ids}")
        return jsonify({'status': 'success', 'report': report_data}), 200

    except Exception as e:
        logger.error(f"Error fetching store comparison report for user ID {current_user_id}: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@reports_bp.route('/clerk-performance', methods=['GET'])
@jwt_required()
@role_required([UserRole.MERCHANT, UserRole.ADMIN])
@cache.cached(timeout=300, key_prefix=lambda: f"clerk_performance_{get_jwt_identity()['id']}_{request.full_path}")
def clerk_performance():
    """Fetch clerk performance report with inventory and sales metrics."""
    try:
        identity = get_jwt_identity()
        current_user_id = identity['id']
        current_user_role = identity['role']
        logger.info(f"Fetching clerk performance report for user ID: {current_user_id}, role: {current_user_role}")

        clerk_id = request.args.get('clerk_id', type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        period = request.args.get('period', 'weekly')

        if period not in ['weekly', 'monthly']:
            logger.error(f"Invalid period provided: {period}")
            return jsonify({'status': 'error', 'message': 'Invalid period. Use weekly or monthly'}), 400

        if start_date and end_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d')
                if start > end:
                    logger.error("Start date is after end date")
                    return jsonify({'status': 'error', 'message': 'Start date must be before end date'}), 400
            except ValueError:
                logger.error(f"Invalid date format: start_date={start_date}, end_date={end_date}")
                return jsonify({'status': 'error', 'message': 'Invalid date format. Use YYYY-MM-DD'}), 400
        else:
            start, end = get_period_dates(period)

        store_ids = get_store_ids(current_user_id, current_user_role)
        if not store_ids:
            logger.warning(f"No accessible stores for user ID: {current_user_id}")
            return jsonify({
                'status': 'success',
                'message': 'No accessible stores for this user',
                'report': []
            }), 200

        clerks_query = db.session.query(User).filter(
            User.role == UserRole.CLERK,
            User.id.in_(
                db.session.query(user_store.c.user_id).filter(
                    user_store.c.store_id.in_(store_ids)
                )
            )
        )
        if clerk_id:
            clerks_query = clerks_query.filter(User.id == clerk_id)
        clerks = clerks_query.all()

        if clerk_id and not clerks:
            logger.error(f"Clerk not found: {clerk_id}")
            return jsonify({'status': 'error', 'message': 'Clerk not found'}), 404

        reports = []
        for clerk in clerks:
            entries = (
                db.session.query(InventoryEntry)
                .filter(
                    InventoryEntry.recorded_by == clerk.id,
                    InventoryEntry.entry_date.between(start, end),
                    InventoryEntry.store_id.in_(store_ids)
                )
                .all()
            )
            sales = (
                db.session.query(SalesRecord)
                .filter(
                    SalesRecord.recorded_by_id == clerk.id,
                    SalesRecord.sale_date.between(start, end),
                    SalesRecord.store_id.in_(store_ids)
                )
                .all()
            )
            total_sales = sum(s.revenue for s in sales)
            spoilage = sum(e.spoilage_quantity * e.buying_price for e in entries if e.spoilage_quantity > 0)
            reports.append({
                'clerk_id': clerk.id,
                'clerk_name': clerk.name,
                'total_entries': len(entries),
                'total_received': sum(e.quantity_received for e in entries),
                'total_spoilage_value': float(spoilage),
                'total_sales': float(total_sales)
            })

        logger.info(f"Clerk performance report retrieved for user ID: {current_user_id}, store IDs: {store_ids}")
        return jsonify({'status': 'success', 'report': reports}), 200

    except Exception as e:
        logger.error(f"Error fetching clerk performance report for user ID {current_user_id}: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@reports_bp.route('/export', methods=['GET'])
@jwt_required()
@role_required([UserRole.MERCHANT, UserRole.ADMIN])
def export_report():
    """Export report as PDF or Excel."""
    try:
        identity = get_jwt_identity()
        current_user_id = identity['id']
        current_user_role = identity['role']
        logger.info(f"Exporting report for user ID: {current_user_id}, role: {current_user_role}")

        report_type = request.args.get('type')
        format = request.args.get('format', 'pdf')
        store_id = request.args.get('store_id', type=int)
        period = request.args.get('period', 'weekly')

        if report_type not in ['sales', 'spoilage', 'payment-status']:
            logger.error(f"Invalid report type provided: {report_type}")
            return jsonify({'status': 'error', 'message': 'Invalid report type. Use sales, spoilage, or payment-status'}), 400
        if format not in ['pdf', 'excel']:
            logger.error(f"Invalid format provided: {format}")
            return jsonify({'status': 'error', 'message': 'Invalid format. Use pdf or excel'}), 400
        if period not in ['weekly', 'monthly'] or (report_type == 'payment-status' and period != 'monthly'):
            logger.error(f"Invalid period provided: {period} for report type: {report_type}")
            return jsonify({'status': 'error', 'message': 'Invalid period. Use weekly or monthly (monthly for payment-status)'}), 400

        start, end = get_period_dates(period)

        store_ids = get_store_ids(current_user_id, current_user_role, store_id)
        if not store_ids:
            logger.warning(f"No accessible stores for user ID: {current_user_id}")
            return jsonify({'status': 'error', 'message': 'No accessible stores for this user'}), 400

        # Fetch data
        data = {}
        if report_type == 'sales':
            sales_data = db.session.query(
                func.coalesce(func.sum(SalesRecord.quantity_sold), 0).label('total_quantity_sold'),
                func.coalesce(func.sum(SalesRecord.revenue), 0).label('total_revenue')
            ).filter(
                SalesRecord.store_id.in_(store_ids),
                SalesRecord.sale_date.between(start, end)
            ).first()
            top_products = (
                db.session.query(
                    Product.name.label('product_name'),
                    func.coalesce(func.sum(SalesRecord.quantity_sold), 0).label('units_sold'),
                    func.coalesce(func.sum(SalesRecord.revenue), 0).label('revenue'),
                    (func.sum(SalesRecord.revenue) / func.sum(SalesRecord.quantity_sold)).label('unit_price')
                )
                .join(SalesRecord, SalesRecord.product_id == Product.id)
                .filter(
                    SalesRecord.store_id.in_(store_ids),
                    SalesRecord.sale_date.between(start, end)
                )
                .group_by(Product.name)
                .order_by(func.sum(SalesRecord.revenue).desc())
                .limit(10 if not store_id else 5)
                .all()
            )
            data = {
                'total_quantity_sold': int(sales_data.total_quantity_sold or 0),
                'total_revenue': float(sales_data.total_revenue or 0),
                'top_products': [
                    {
                        'product_name': p.product_name,
                        'units_sold': int(p.units_sold or 0),
                        'revenue': float(p.revenue or 0),
                        'unit_price': float(p.unit_price or 0) if p.units_sold > 0 else 0.0
                    } for p in top_products
                ]
            }
        elif report_type == 'spoilage':
            spoilage_query = (
                db.session.query(InventoryEntry)
                .join(Product, Product.id == InventoryEntry.product_id)
                .filter(
                    InventoryEntry.store_id.in_(store_ids),
                    InventoryEntry.entry_date.between(start, end),
                    InventoryEntry.spoilage_quantity > 0
                )
            )
            total_spoilage = spoilage_query.with_entities(
                func.sum(InventoryEntry.spoilage_quantity * InventoryEntry.buying_price)
            ).scalar() or 0.0
            category_data = (
                spoilage_query.join(ProductCategory, Product.category_id == ProductCategory.id)
                .group_by(ProductCategory.name)
                .with_entities(
                    ProductCategory.name.label('category_name'),
                    func.sum(InventoryEntry.spoilage_quantity).label('spoilage_quantity')
                )
                .all()
            )
            total_spoilage_quantity = sum(cat.spoilage_quantity for cat in category_data) or 1
            data = {
                'total_ksh': float(total_spoilage),
                'categories': [
                    {
                        'category_name': r.category_name,
                        'spoilage_percentage': float((r.spoilage_quantity / total_spoilage_quantity * 100) if total_spoilage_quantity > 0 else 0)
                    } for r in category_data
                ]
            }
        else:  # payment-status
            payment_data = db.session.query(
                func.coalesce(func.sum(func.case(
                    [(InventoryEntry.payment_status == PaymentStatus.PAID, InventoryEntry.buying_price * InventoryEntry.quantity_received)],
                    else_=0
                )), 0).label('total_paid'),
                func.coalesce(func.sum(func.case(
                    [(InventoryEntry.payment_status == PaymentStatus.UNPAID, InventoryEntry.buying_price * InventoryEntry.quantity_received)],
                    else_=0
                )), 0).label('total_unpaid')
            ).filter(
                InventoryEntry.store_id.in_(store_ids),
                InventoryEntry.entry_date.between(start, end)
            ).first()
            suppliers = (
                db.session.query(
                    Supplier.name.label('supplier_name'),
                    Product.name.label('product_name'),
                    func.coalesce(func.sum(InventoryEntry.buying_price * InventoryEntry.quantity_received), 0).label('amount_due'),
                    InventoryEntry.due_date
                )
                .join(InventoryEntry, InventoryEntry.supplier_id == Supplier.id)
                .join(Product, InventoryEntry.product_id == Product.id)
                .filter(
                    InventoryEntry.store_id.in_(store_ids),
                    InventoryEntry.entry_date.between(start, end)
                )
                .group_by(Supplier.name, Product.name, InventoryEntry.due_date)
                .all()
            )
            data = {
                'total_paid': float(payment_data.total_paid or 0),
                'total_unpaid': float(payment_data.total_unpaid or 0),
                'suppliers': [
                    {
                        'supplier_name': s.supplier_name,
                        'product_name': s.product_name,
                        'amount_due': float(s.amount_due or 0),
                        'due_date': s.due_date.isoformat() if s.due_date else 'N/A'
                    } for s in suppliers
                ]
            }

        # Generate report
        if format == 'pdf':
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            elements = []

            styles = getSampleStyleSheet()
            elements.append(Paragraph(f"MyDuka {report_type.replace('-', ' ').title()} Report", styles['Title']))
            elements.append(Paragraph(f"Generated on {datetime.utcnow().strftime('%Y-%m-%d')}", styles['Normal']))

            table_data = []
            if report_type == 'sales':
                table_data.append(['Total Quantity Sold', 'Total Revenue'])
                table_data.append([str(data['total_quantity_sold']), f"KSh {data['total_revenue']:.2f}"])
                table_data.append([''] * 2)
                table_data.append(['Product', 'Units Sold', 'Revenue', 'Unit Price'])
                for p in data['top_products']:
                    table_data.append([p['product_name'], str(p['units_sold']), f"KSh {p['revenue']:.2f}", f"KSh {p['unit_price']:.2f}"])
            elif report_type == 'spoilage':
                table_data.append(['Total Spoilage (KSh)'])
                table_data.append([f"KSh {data['total_ksh']:.2f}"])
                table_data.append([''] * 1)
                table_data.append(['Category', 'Spoilage Percentage'])
                for row in data['categories']:
                    table_data.append([row['category_name'], f"{row['spoilage_percentage']:.2f}%"])
            else:
                table_data.append(['Total Paid', 'Total Unpaid'])
                table_data.append([
                    f"KSh {data['total_paid']:.2f}",
                    f"KSh {data['total_unpaid']:.2f}"
                ])
                table_data.append([''] * 2)
                table_data.append(['Supplier', 'Product', 'Amount Due', 'Due Date'])
                for s in data['suppliers']:
                    table_data.append([
                        s['supplier_name'],
                        s['product_name'],
                        f"KSh {s['amount_due']:.2f}",
                        s['due_date'] if s['due_date'] != 'N/A' else 'N/A'
                    ])

            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 14),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(table)

            doc.build(elements)
            buffer.seek(0)
            logger.info(f"PDF report exported for type {report_type} by user ID: {current_user_id}")
            return send_file(
                buffer,
                as_attachment=True,
                download_name=f"{report_type}_report.pdf",
                mimetype='application/pdf'
            )
        else:  # excel
            workbook = openpyxl.Workbook()
            sheet = workbook.active
            sheet.title = report_type.replace('-', ' ').title()

            if report_type == 'sales':
                sheet.append(['Total Quantity Sold', 'Total Revenue'])
                sheet.append([data['total_quantity_sold'], data['total_revenue']])
                sheet.append([''] * 2)
                sheet.append(['Product', 'Units Sold', 'Revenue', 'Unit Price'])
                for p in data['top_products']:
                    sheet.append([p['product_name'], p['units_sold'], p['revenue'], p['unit_price']])
            elif report_type == 'spoilage':
                sheet.append(['Total Spoilage (KSh)'])
                sheet.append([data['total_ksh']])
                sheet.append([''] * 1)
                sheet.append(['Category', 'Spoilage Percentage'])
                for row in data['categories']:
                    sheet.append([row['category_name'], row['spoilage_percentage']])
            else:
                sheet.append(['Total Paid', 'Total Unpaid'])
                sheet.append([data['total_paid'], data['total_unpaid']])
                sheet.append([''] * 2)
                sheet.append(['Supplier', 'Product', 'Amount Due', 'Due Date'])
                for s in data['suppliers']:
                    sheet.append([
                        s['supplier_name'],
                        s['product_name'],
                        s['amount_due'],
                        s['due_date'] if s['due_date'] != 'N/A' else 'N/A'
                    ])

            buffer = BytesIO()
            workbook.save(buffer)
            buffer.seek(0)
            logger.info(f"Excel report exported for type {report_type} by user ID: {current_user_id}")
            return send_file(
                buffer,
                as_attachment=True,
                download_name=f"{report_type}_report.xlsx",
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )

    except Exception as e:
        logger.error(f"Error exporting report for user ID {current_user_id}: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500