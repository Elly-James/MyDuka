from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func, types
from datetime import datetime, timedelta
import logging
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import openpyxl
from io import BytesIO

from extensions import db, cache
from models import User, UserRole, InventoryEntry, Product, Store, PaymentStatus, ProductCategory
from schemas import SalesReportSchema, SpoilageReportSchema, PaymentStatusReportSchema, StoreComparisonReportSchema, ClerkPerformanceReportSchema, SalesChartDataSchema, ChartDataSchema

reports_bp = Blueprint('reports', __name__, url_prefix='/api/reports')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@reports_bp.route('/sales', methods=['GET'])
@jwt_required()
@cache.cached(timeout=3600, query_string=True)
def get_sales_report():
    """
    Get sales report (weekly, monthly, annual).

    Query Parameters:
        - period (str): Report period ('weekly', 'monthly', 'annual') - default 'weekly'
        - store_id (int, optional): Filter by store ID (for Merchants)
        - product_id (int, optional): Filter by product ID
        - start_date (str, optional): Start date in YYYY-MM-DD format
        - end_date (str, optional): End date in YYYY-MM-DD format

    Responses:
        - 200: Sales report data
        - 400: Invalid period or date format
        - 403: Unauthorized access
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
        
        period = request.args.get('period', 'weekly')
        store_id = request.args.get('store_id', type=int)
        product_id = request.args.get('product_id', type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if period not in ['weekly', 'monthly', 'annual']:
            return jsonify({
                'status': 'error',
                'message': 'Invalid period. Use weekly, monthly, or annual'
            }), 400
        
        # Date filtering
        if start_date and end_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d')
                if start > end:
                    return jsonify({
                        'status': 'error',
                        'message': 'Start date must be before end date'
                    }), 400
            except ValueError:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid date format. Use YYYY-MM-DD'
                }), 400
        
        # Build query
        if period == 'weekly':
            query = db.session.query(
                func.concat(
                    func.extract('year', InventoryEntry.entry_date),
                    '-W',
                    func.lpad(
                        func.extract('week', InventoryEntry.entry_date).cast(types.Text),
                        2,
                        '0'
                    )
                ).label('time_period'),
                func.sum(InventoryEntry.quantity_received).label('total_received'),
                func.sum(InventoryEntry.quantity_spoiled).label('total_spoiled'),
                func.sum(InventoryEntry.selling_price * InventoryEntry.quantity_received).label('total_sales')
            ).join(Product, InventoryEntry.product_id == Product.id)
        else:
            query = db.session.query(
                func.date_trunc(period, InventoryEntry.entry_date).label('time_period'),
                func.sum(InventoryEntry.quantity_received).label('total_received'),
                func.sum(InventoryEntry.quantity_spoiled).label('total_spoiled'),
                func.sum(InventoryEntry.selling_price * InventoryEntry.quantity_received).label('total_sales')
            ).join(Product, InventoryEntry.product_id == Product.id)
        
        if product_id:
            query = query.filter(InventoryEntry.product_id == product_id)
        
        if start_date and end_date:
            query = query.filter(InventoryEntry.entry_date.between(start, end))
        
        if current_user.role != UserRole.MERCHANT:
            query = query.filter(Product.store_id == current_user.store_id)
        elif store_id:
            query = query.filter(Product.store_id == store_id)
        
        query = query.group_by('time_period').order_by('time_period')
        results = query.all()
        
        labels = []
        sales_data = []
        spoilage_data = []
        total_quantity_sold = 0
        total_revenue = 0.0
        
        for row in results:
            labels.append(str(row.time_period))
            sales_data.append(float(row.total_sales) if row.total_sales else 0.0)
            spoilage_data.append(int(row.total_spoiled))
            total_quantity_sold += int(row.total_received)
            total_revenue += float(row.total_sales) if row.total_sales else 0.0
        
        # Prepare report data
        report_data = {
            'total_quantity_sold': total_quantity_sold,
            'total_revenue': total_revenue,
            'chart_data': {
                'labels': labels,
                'datasets': [
                    {'label': 'Sales', 'data': sales_data},
                    {'label': 'Spoilage', 'data': spoilage_data}
                ]
            }
        }
        
        # Use SalesReportSchema to serialize the report data
        sales_report_schema = SalesReportSchema()
        serialized_report = sales_report_schema.dump(report_data)
        
        logger.info(f"Sales report retrieved for user ID: {current_user_id}, period: {period}")
        return jsonify({
            'status': 'success',
            'report': serialized_report
        }), 200
    except Exception as e:
        logger.error(f"Error in get_sales_report for user ID {current_user_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

@reports_bp.route('/spoilage', methods=['GET'])
@jwt_required()
@cache.cached(timeout=3600, query_string=True)
def get_spoilage_report():
    """
    Get spoilage report by category.

    Query Parameters:
        - store_id (int, optional): Filter by store ID (for Merchants)
        - start_date (str, optional): Start date in YYYY-MM-DD format
        - end_date (str, optional): End date in YYYY-MM-DD format

    Responses:
        - 200: Spoilage report data
        - 400: Invalid date format
        - 403: Unauthorized access
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
        
        store_id = request.args.get('store_id', type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Date filtering
        if start_date and end_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d')
                if start > end:
                    return jsonify({
                        'status': 'error',
                        'message': 'Start date must be before end date'
                    }), 400
            except ValueError:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid date format. Use YYYY-MM-DD'
                }), 400
        
        query = db.session.query(
            ProductCategory.name.label('category_name'),
            func.sum(InventoryEntry.quantity_spoiled).label('total_spoiled')
        ).join(Product, InventoryEntry.product_id == Product.id).\
         join(ProductCategory, Product.category_id == ProductCategory.id)
        
        if start_date and end_date:
            query = query.filter(InventoryEntry.entry_date.between(start, end))
        
        if current_user.role != UserRole.MERCHANT:
            query = query.filter(Product.store_id == current_user.store_id)
        elif store_id:
            query = query.filter(Product.store_id == store_id)
        
        query = query.group_by(ProductCategory.name)
        results = query.all()
        
        labels = []
        data = []
        total_spoilage = 0
        
        for row in results:
            labels.append(row.category_name)
            data.append(int(row.total_spoiled))
            total_spoilage += int(row.total_spoiled)
        
        # Prepare report data
        report_data = {
            'total_spoilage': total_spoilage,
            'chart_data': {
                'labels': labels,
                'datasets': [{'label': 'Spoilage', 'data': data}]
            }
        }
        
        # Use SpoilageReportSchema to serialize the report data
        spoilage_report_schema = SpoilageReportSchema()
        serialized_report = spoilage_report_schema.dump(report_data)
        
        logger.info(f"Spoilage report retrieved for user ID: {current_user_id}")
        return jsonify({
            'status': 'success',
            'report': serialized_report
        }), 200
    except Exception as e:
        logger.error(f"Error in get_spoilage_report for user ID {current_user_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

@reports_bp.route('/payment-status', methods=['GET'])
@jwt_required()
@cache.cached(timeout=3600, query_string=True)
def get_payment_status_report():
    """
    Get paid vs unpaid report.

    Query Parameters:
        - store_id (int, optional): Filter by store ID (for Merchants)
        - start_date (str, optional): Start date in YYYY-MM-DD format
        - end_date (str, optional): End date in YYYY-MM-DD format

    Responses:
        - 200: Payment status report data
        - 400: Invalid date format
        - 403: Unauthorized access
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
        
        store_id = request.args.get('store_id', type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Date filtering
        if start_date and end_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d')
                if start > end:
                    return jsonify({
                        'status': 'error',
                        'message': 'Start date must be before end date'
                    }), 400
            except ValueError:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid date format. Use YYYY-MM-DD'
                }), 400
        
        query = db.session.query(
            InventoryEntry.payment_status,
            func.count(InventoryEntry.id).label('count'),
            func.sum(InventoryEntry.buying_price * InventoryEntry.quantity_received).label('total_amount')
        ).join(Product, InventoryEntry.product_id == Product.id)
        
        if start_date and end_date:
            query = query.filter(InventoryEntry.entry_date.between(start, end))
        
        if current_user.role != UserRole.MERCHANT:
            query = query.filter(Product.store_id == current_user.store_id)
        elif store_id:
            query = query.filter(Product.store_id == store_id)
        
        query = query.group_by(InventoryEntry.payment_status)
        results = query.all()
        
        labels = ['Paid', 'Unpaid']
        data = [0, 0]
        total_paid = 0.0
        total_unpaid = 0.0
        
        for row in results:
            amount = float(row.total_amount) if row.total_amount else 0.0
            if row.payment_status == PaymentStatus.PAID:
                data[0] = amount
                total_paid = amount
            else:
                data[1] = amount
                total_unpaid = amount
        
        # Prepare report data
        report_data = {
            'total_paid': total_paid,
            'total_unpaid': total_unpaid,
            'chart_data': {
                'labels': labels,
                'datasets': [{'label': 'Payment Status', 'data': data}]
            }
        }
        
        # Use PaymentStatusReportSchema to serialize the report data
        payment_status_report_schema = PaymentStatusReportSchema()
        serialized_report = payment_status_report_schema.dump(report_data)
        
        logger.info(f"Payment status report retrieved for user ID: {current_user_id}")
        return jsonify({
            'status': 'success',
            'report': serialized_report
        }), 200
    except Exception as e:
        logger.error(f"Error in get_payment_status_report for user ID {current_user_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

@reports_bp.route('/store-comparison', methods=['GET'])
@jwt_required()
@cache.cached(timeout=3600, query_string=True)
def store_comparison():
    """
    Get sales and spoilage comparison across all stores (Merchants only).

    Query Parameters:
        - start_date (str, optional): Start date in YYYY-MM-DD format
        - end_date (str, optional): End date in YYYY-MM-DD format

    Responses:
        - 200: Store comparison report data
        - 400: Invalid date format
        - 403: Unauthorized access
        - 404: User not found
        - 500: Internal server error
    """
    try:
        current_user_id = get_jwt_identity()['id']
        current_user = db.session.get(User, current_user_id)
        
        if not current_user or current_user.role != UserRole.MERCHANT:
            return jsonify({
                'status': 'error',
                'message': 'Unauthorized to view store comparison'
            }), 403
        
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Date filtering
        if start_date and end_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d')
                if start > end:
                    return jsonify({
                        'status': 'error',
                        'message': 'Start date must be before end date'
                    }), 400
            except ValueError:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid date format. Use YYYY-MM-DD'
                }), 400
        
        query = db.session.query(
            Store.name.label('store_name'),
            func.sum(InventoryEntry.quantity_received).label('total_received'),
            func.sum(InventoryEntry.quantity_spoiled).label('total_spoiled'),
            func.sum(InventoryEntry.selling_price * InventoryEntry.quantity_received).label('total_sales')
        ).join(Product, InventoryEntry.product_id == Product.id).\
         join(Store, Product.store_id == Store.id)
        
        if start_date and end_date:
            query = query.filter(InventoryEntry.entry_date.between(start, end))
        
        query = query.group_by(Store.name)
        results = query.all()
        
        labels = []
        sales_data = []
        spoilage_data = []
        
        for row in results:
            labels.append(row.store_name)
            sales_data.append(float(row.total_sales) if row.total_sales else 0.0)
            spoilage_data.append(int(row.total_spoiled))
        
        # Prepare report data
        report_data = {
            'chart_data': {
                'labels': labels,
                'datasets': [
                    {'label': 'Sales', 'data': sales_data},
                    {'label': 'Spoilage', 'data': spoilage_data}
                ]
            }
        }
        
        # Use StoreComparisonReportSchema to serialize the report data
        store_comparison_report_schema = StoreComparisonReportSchema()
        serialized_report = store_comparison_report_schema.dump(report_data)
        
        logger.info(f"Store comparison report retrieved for user ID: {current_user_id}")
        return jsonify({
            'status': 'success',
            'report': serialized_report
        }), 200
    except Exception as e:
        logger.error(f"Error in store_comparison for user ID {current_user_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

@reports_bp.route('/sales/chart-data', methods=['GET'])
@jwt_required()
@cache.cached(timeout=3600, query_string=True)
def sales_chart_data():
    """
    Get chart-ready sales data for weekly, monthly, annual periods.

    Query Parameters:
        - store_id (int, optional): Filter by store ID (for Merchants)
        - product_id (int, optional): Filter by product ID
        - start_date (str, optional): Start date in YYYY-MM-DD format
        - end_date (str, optional): End date in YYYY-MM-DD format

    Responses:
        - 200: Chart-ready sales data
        - 400: Invalid date format
        - 403: Unauthorized access
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
        
        store_id = request.args.get('store_id', type=int)
        product_id = request.args.get('product_id', type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Date filtering
        if start_date and end_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d')
                if start > end:
                    return jsonify({
                        'status': 'error',
                        'message': 'Start date must be before end date'
                    }), 400
            except ValueError:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid date format. Use YYYY-MM-DD'
                }), 400
        
        result = {}
        for period in ['weekly', 'monthly', 'annual']:
            if period == 'weekly':
                query = db.session.query(
                    func.concat(
                        func.extract('year', InventoryEntry.entry_date),
                        '-W',
                        func.lpad(
                            func.extract('week', InventoryEntry.entry_date).cast(types.Text),
                            2,
                            '0'
                        )
                    ).label('time_period'),
                    func.sum(InventoryEntry.quantity_received).label('total_received'),
                    func.sum(InventoryEntry.quantity_spoiled).label('total_spoiled'),
                    func.sum(InventoryEntry.selling_price * InventoryEntry.quantity_received).label('total_sales')
                ).join(Product, InventoryEntry.product_id == Product.id)
            else:
                query = db.session.query(
                    func.date_trunc(period, InventoryEntry.entry_date).label('time_period'),
                    func.sum(InventoryEntry.quantity_received).label('total_received'),
                    func.sum(InventoryEntry.quantity_spoiled).label('total_spoiled'),
                    func.sum(InventoryEntry.selling_price * InventoryEntry.quantity_received).label('total_sales')
                ).join(Product, InventoryEntry.product_id == Product.id)
            
            if product_id:
                query = query.filter(InventoryEntry.product_id == product_id)
            
            if start_date and end_date:
                query = query.filter(InventoryEntry.entry_date.between(start, end))
            
            if current_user.role != UserRole.MERCHANT:
                query = query.filter(Product.store_id == current_user.store_id)
            elif store_id:
                query = query.filter(Product.store_id == store_id)
            
            query = query.group_by('time_period').order_by('time_period')
            results = query.all()
            
            labels = []
            sales_data = []
            spoilage_data = []
            
            for row in results:
                labels.append(str(row.time_period))
                sales_data.append(float(row.total_sales) if row.total_sales else 0.0)
                spoilage_data.append(int(row.total_spoiled))
            
            result[period] = {
                'labels': labels,
                'datasets': [
                    {'label': 'Sales', 'data': sales_data},
                    {'label': 'Spoilage', 'data': spoilage_data}
                ]
            }
        
        # Use SalesChartDataSchema to serialize the chart data
        sales_chart_data_schema = SalesChartDataSchema()
        serialized_chart_data = sales_chart_data_schema.dump(result)
        
        logger.info(f"Sales chart data retrieved for user ID: {current_user_id}")
        return jsonify({
            'status': 'success',
            'chart_data': serialized_chart_data
        }), 200
    except Exception as e:
        logger.error(f"Error in sales_chart_data for user ID {current_user_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

@reports_bp.route('/clerk-performance', methods=['GET'])
@jwt_required()
def clerk_performance():
    """
    Get performance report for a specific clerk.

    Query Parameters:
        - clerk_id (int): ID of the clerk to evaluate
        - start_date (str, optional): Start date in YYYY-MM-DD format
        - end_date (str, optional): End date in YYYY-MM-DD format

    Responses:
        - 200: Clerk performance report
        - 400: Missing or invalid clerk ID, or invalid date format
        - 403: Unauthorized access
        - 404: User or clerk not found
        - 500: Internal server error
    """
    try:
        current_user_id = get_jwt_identity()['id']
        current_user = db.session.get(User, current_user_id)
        
        if not current_user or current_user.role == UserRole.CLERK:
            return jsonify({
                'status': 'error',
                'message': 'Unauthorized to view clerk performance'
            }), 403
        
        clerk_id = request.args.get('clerk_id', type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not clerk_id:
            return jsonify({
                'status': 'error',
                'message': 'Clerk ID is required'
            }), 400
        
        clerk = db.session.get(User, clerk_id)
        if not clerk or clerk.role != UserRole.CLERK:
            return jsonify({
                'status': 'error',
                'message': 'Clerk not found'
            }), 404
        
        if current_user.role == UserRole.ADMIN and current_user.store_id != clerk.store_id:
            return jsonify({
                'status': 'error',
                'message': 'You can only view clerks in your store'
            }), 403
        
        # Date filtering
        if start_date and end_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d')
                if start > end:
                    return jsonify({
                        'status': 'error',
                        'message': 'Start date must be before end date'
                    }), 400
            except ValueError:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid date format. Use YYYY-MM-DD'
                }), 400
        
        query = db.session.query(
            func.count(InventoryEntry.id).label('total_entries'),
            func.sum(InventoryEntry.quantity_received).label('total_received'),
            func.sum(InventoryEntry.quantity_spoiled).label('total_spoiled'),
            func.sum(InventoryEntry.selling_price * InventoryEntry.quantity_received).label('total_sales')
        ).filter(InventoryEntry.recorded_by == clerk_id)
        
        if start_date and end_date:
            query = query.filter(InventoryEntry.entry_date.between(start, end))
        
        result = query.first()
        
        # Prepare report data
        report_data = {
            'clerk_id': clerk_id,
            'clerk_name': clerk.name,
            'total_entries': result.total_entries or 0,
            'total_received': result.total_received or 0,
            'total_spoiled': result.total_spoiled or 0,
            'total_sales': float(result.total_sales) if result.total_sales else 0.0
        }
        
        # Use ClerkPerformanceReportSchema to serialize the report data
        clerk_performance_report_schema = ClerkPerformanceReportSchema()
        serialized_report = clerk_performance_report_schema.dump(report_data)
        
        logger.info(f"Clerk performance report retrieved for clerk ID: {clerk_id} by user ID: {current_user_id}")
        return jsonify({
            'status': 'success',
            'report': serialized_report
        }), 200
    except Exception as e:
        logger.error(f"Error in clerk_performance for user ID {current_user_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

@reports_bp.route('/export', methods=['GET'])
@jwt_required()
def export_report():
    """
    Export report as PDF or Excel.

    Query Parameters:
        - type (str): Report type ('sales', 'spoilage', 'payment-status')
        - format (str): Export format ('pdf', 'excel') - default 'pdf'
        - store_id (int, optional): Filter by store ID (for Merchants)

    Responses:
        - 200: Report file
        - 400: Invalid report type or format
        - 403: Unauthorized access
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
        
        report_type = request.args.get('type')
        format = request.args.get('format', 'pdf')
        store_id = request.args.get('store_id', type=int)
        
        if report_type not in ['sales', 'spoilage', 'payment-status']:
            return jsonify({
                'status': 'error',
                'message': 'Invalid report type. Use sales, spoilage, or payment-status'
            }), 400
        
        if format not in ['pdf', 'excel']:
            return jsonify({
                'status': 'error',
                'message': 'Invalid format. Use pdf or excel'
            }), 400
        
        # Fetch data based on report type
        if report_type == 'sales':
            query = db.session.query(
                Store.name.label('store_name'),
                func.sum(InventoryEntry.quantity_received).label('total_received'),
                func.sum(InventoryEntry.quantity_spoiled).label('total_spoiled'),
                func.sum(InventoryEntry.selling_price * InventoryEntry.quantity_received).label('total_sales')
            ).join(Product, InventoryEntry.product_id == Product.id).\
             join(Store, Product.store_id == Store.id)
            
            if current_user.role != UserRole.MERCHANT:
                query = query.filter(Product.store_id == current_user.store_id)
            elif store_id:
                query = query.filter(Product.store_id == store_id)
            
            query = query.group_by(Store.name)
            data = query.all()
        
        elif report_type == 'spoilage':
            query = db.session.query(
                ProductCategory.name.label('category_name'),
                func.sum(InventoryEntry.quantity_spoiled).label('total_spoiled')
            ).join(Product, InventoryEntry.product_id == Product.id).\
             join(ProductCategory, Product.category_id == ProductCategory.id)
            
            if current_user.role != UserRole.MERCHANT:
                query = query.filter(Product.store_id == current_user.store_id)
            elif store_id:
                query = query.filter(Product.store_id == store_id)
            
            query = query.group_by(ProductCategory.name)
            data = query.all()
        
        else:  # payment-status
            query = db.session.query(
                InventoryEntry.payment_status,
                func.count(InventoryEntry.id).label('count'),
                func.sum(InventoryEntry.buying_price * InventoryEntry.quantity_received).label('total_amount')
            ).join(Product, InventoryEntry.product_id == Product.id)
            
            if current_user.role != UserRole.MERCHANT:
                query = query.filter(Product.store_id == current_user.store_id)
            elif store_id:
                query = query.filter(Product.store_id == store_id)
            
            query = query.group_by(InventoryEntry.payment_status)
            data = query.all()
        
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
                table_data.append(['Store', 'Total Received', 'Total Spoiled', 'Total Sales'])
                for row in data:
                    table_data.append([
                        row.store_name,
                        str(row.total_received),
                        str(row.total_spoiled),
                        f"${row.total_sales:.2f}" if row.total_sales else "0.00"
                    ])
            elif report_type == 'spoilage':
                table_data.append(['Category', 'Total Spoiled'])
                for row in data:
                    table_data.append([row.category_name, str(row.total_spoiled)])
            else:
                table_data.append(['Payment Status', 'Count', 'Total Amount'])
                for row in data:
                    table_data.append([
                        row.payment_status.name,
                        str(row.count),
                        f"${row.total_amount:.2f}" if row.total_amount else "0.00"
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
                sheet.append(['Store', 'Total Received', 'Total Spoiled', 'Total Sales'])
                for row in data:
                    sheet.append([
                        row.store_name,
                        row.total_received,
                        row.total_spoiled,
                        row.total_sales if row.total_sales else 0.0
                    ])
            elif report_type == 'spoilage':
                sheet.append(['Category', 'Total Spoiled'])
                for row in data:
                    sheet.append([row.category_name, row.total_spoiled])
            else:
                sheet.append(['Payment Status', 'Count', 'Total Amount'])
                for row in data:
                    sheet.append([
                        row.payment_status.name,
                        row.count,
                        row.total_amount if row.total_amount else 0.0
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
        logger.error(f"Error in export_report for user ID {current_user_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

@reports_bp.route('/chart-data/sales-trend', methods=['GET'])
@jwt_required()
@cache.cached(timeout=3600, query_string=True)
def sales_trend_chart():
    """
    Get chart-ready sales trend data for specified period.

    Query Parameters:
        - period (str): Report period ('weekly', 'monthly', 'annual') - default 'weekly'
        - store_id (int, optional): Filter by store ID (for Merchants)
        - start_date (str, optional): Start date in YYYY-MM-DD format
        - end_date (str, optional): End date in YYYY-MM-DD format

    Responses:
        - 200: Sales trend chart data
        - 400: Invalid period or date format
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
        
        period = request.args.get('period', 'weekly')
        store_id = request.args.get('store_id', type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if period not in ['weekly', 'monthly', 'annual']:
            return jsonify({
                'status': 'error',
                'message': 'Invalid period. Use weekly, monthly, or annual'
            }), 400
        
        # Date filtering
        if start_date and end_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d')
                if start > end:
                    return jsonify({
                        'status': 'error',
                        'message': 'Start date must be before end date'
                    }), 400
            except ValueError:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid date format. Use YYYY-MM-DD'
                }), 400
        
        # Base query
        query = db.session.query(
            func.date_trunc(period, InventoryEntry.entry_date).label('period'),
            func.sum(InventoryEntry.quantity_received * InventoryEntry.selling_price).label('sales')
        ).join(Product, InventoryEntry.product_id == Product.id)
        
        # Apply filters
        if current_user.role != UserRole.MERCHANT:
            query = query.filter(Product.store_id == current_user.store_id)
        elif store_id:
            query = query.filter(Product.store_id == store_id)
        
        if start_date and end_date:
            query = query.filter(InventoryEntry.entry_date.between(start, end))
        
        results = query.group_by('period').order_by('period').all()
        
        # Prepare chart data
        chart_data = {
            'labels': [r.period.strftime('%Y-%m-%d') for r in results],
            'datasets': [{
                'label': 'Sales',
                'data': [float(r.sales) for r in results],
                'backgroundColor': '#2E3A8C'
            }]
        }
        
        # Use ChartDataSchema to serialize the chart data
        chart_data_schema = ChartDataSchema()
        serialized_chart_data = chart_data_schema.dump(chart_data)
        
        logger.info(f"Sales trend chart data retrieved for user ID: {current_user_id}, period: {period}")
        return jsonify({
            'status': 'success',
            'chart_data': serialized_chart_data
        }), 200
    except Exception as e:
        logger.error(f"Error in sales_trend_chart for user ID {current_user_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

@reports_bp.route('/chart-data/spoilage-by-category', methods=['GET'])
@jwt_required()
@cache.cached(timeout=3600, query_string=True)
def spoilage_by_category():
    """
    Get chart-ready spoilage data by product category.

    Query Parameters:
        - store_id (int, optional): Filter by store ID (for Merchants)
        - start_date (str, optional): Start date in YYYY-MM-DD format
        - end_date (str, optional): End date in YYYY-MM-DD format

    Responses:
        - 200: Spoilage by category chart data
        - 400: Invalid date format
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
        
        store_id = request.args.get('store_id', type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Date filtering
        if start_date and end_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d')
                if start > end:
                    return jsonify({
                        'status': 'error',
                        'message': 'Start date must be before end date'
                    }), 400
            except ValueError:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid date format. Use YYYY-MM-DD'
                }), 400
        
        # Base query
        query = db.session.query(
            ProductCategory.name.label('category_name'),
            func.sum(InventoryEntry.quantity_spoiled).label('total_spoiled')
        ).join(Product, InventoryEntry.product_id == Product.id).\
         join(ProductCategory, Product.category_id == ProductCategory.id)
        
        # Apply filters
        if current_user.role != UserRole.MERCHANT:
            query = query.filter(Product.store_id == current_user.store_id)
        elif store_id:
            query = query.filter(Product.store_id == store_id)
        
        if start_date and end_date:
            query = query.filter(InventoryEntry.entry_date.between(start, end))
        
        results = query.group_by(ProductCategory.name).order_by(ProductCategory.name).all()
        
        # Prepare chart data
        chart_data = {
            'labels': [r.category_name for r in results],
            'datasets': [{
                'label': 'Spoilage',
                'data': [int(r.total_spoiled) for r in results],
                'backgroundColor': '#2E3A8C'
            }]
        }
        
        # Use ChartDataSchema to serialize the chart data
        chart_data_schema = ChartDataSchema()
        serialized_chart_data = chart_data_schema.dump(chart_data)
        
        logger.info(f"Spoilage by category chart data retrieved for user ID: {current_user_id}")
        return jsonify({
            'status': 'success',
            'chart_data': serialized_chart_data
        }), 200
    except Exception as e:
        logger.error(f"Error in spoilage_by_category for user ID {current_user_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500