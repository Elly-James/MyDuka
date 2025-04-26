# routes/reports.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func, types  # Import types for proper casting
from datetime import datetime

from extensions import db
from models import User, UserRole, InventoryEntry, Product, Store, PaymentStatus, ProductCategory

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/sales', methods=['GET'])
@jwt_required()
def get_sales_report():
    """Get sales report (weekly, monthly, annual)"""
    current_user_id = get_jwt_identity()['id']
    current_user = db.session.get(User, current_user_id)
    
    if not current_user:
        return jsonify({
            'status': 'error',
            'message': 'User not found'
        }), 404
    
    # Get query parameters
    period = request.args.get('period', 'weekly')  # weekly, monthly, annual
    store_id = request.args.get('store_id', type=int)
    product_id = request.args.get('product_id', type=int)
    
    # Validate period
    if period not in ['weekly', 'monthly', 'annual']:
        return jsonify({
            'status': 'error',
            'message': 'Invalid period. Use weekly, monthly, or annual'
        }), 400
    
    # Build query
    if period == 'weekly':
        # Use EXTRACT to group by week and year, with proper type casting
        query = db.session.query(
            func.concat(
                func.extract('year', InventoryEntry.entry_date),
                '-W',
                func.lpad(
                    func.extract('week', InventoryEntry.entry_date).cast(types.Text),  # Use types.Text instead of 'text'
                    2,
                    '0'
                )
            ).label('time_period'),
            func.sum(InventoryEntry.quantity_received).label('total_received'),
            func.sum(InventoryEntry.quantity_spoiled).label('total_spoiled'),
            func.sum(InventoryEntry.selling_price * InventoryEntry.quantity_received).label('total_sales')
        ).join(Product, InventoryEntry.product_id == Product.id)
    else:
        # For monthly and annual, use date_trunc
        query = db.session.query(
            func.date_trunc(period, InventoryEntry.entry_date).label('time_period'),
            func.sum(InventoryEntry.quantity_received).label('total_received'),
            func.sum(InventoryEntry.quantity_spoiled).label('total_spoiled'),
            func.sum(InventoryEntry.selling_price * InventoryEntry.quantity_received).label('total_sales')
        ).join(Product, InventoryEntry.product_id == Product.id)
    
    # Apply filters
    if product_id:
        query = query.filter(InventoryEntry.product_id == product_id)
    
    # Restrict to user's store if not merchant
    if current_user.role != UserRole.MERCHANT:
        query = query.filter(Product.store_id == current_user.store_id)
    elif store_id:
        query = query.filter(Product.store_id == store_id)
    
    # Group by time period
    query = query.group_by('time_period').order_by('time_period')
    
    # Execute query
    results = query.all()
    
    # Prepare response
    report_data = {
        'total_quantity_sold': 0,
        'total_revenue': 0.0
    }
    for row in results:
        report_data['total_quantity_sold'] += int(row.total_received)
        report_data['total_revenue'] += float(row.total_sales) if row.total_sales else 0.0
    
    return jsonify({
        'status': 'success',
        'report': report_data
    }), 200

@reports_bp.route('/spoilage', methods=['GET'])
@jwt_required()
def get_spoilage_report():
    """Get spoilage report by category"""
    current_user_id = get_jwt_identity()['id']
    current_user = db.session.get(User, current_user_id)
    
    if not current_user:
        return jsonify({
            'status': 'error',
            'message': 'User not found'
        }), 404
    
    # Get query parameters
    store_id = request.args.get('store_id', type=int)
    
    # Build query
    query = db.session.query(
        Product.category_id,
        func.sum(InventoryEntry.quantity_spoiled).label('total_spoiled')
    ).join(Product, InventoryEntry.product_id == Product.id)
    
    # Restrict to user's store if not merchant
    if current_user.role != UserRole.MERCHANT:
        query = query.filter(Product.store_id == current_user.store_id)
    elif store_id:
        query = query.filter(Product.store_id == store_id)
    
    # Group by category
    query = query.group_by(Product.category_id)
    
    # Execute query
    results = query.all()
    
    # Prepare response
    total_spoilage = sum(int(row.total_spoiled) for row in results)
    
    return jsonify({
        'status': 'success',
        'report': {
            'total_spoilage': total_spoilage
        }
    }), 200

@reports_bp.route('/payment-status', methods=['GET'])
@jwt_required()
def get_payment_status_report():
    """Get paid vs unpaid report"""
    current_user_id = get_jwt_identity()['id']
    current_user = db.session.get(User, current_user_id)
    
    if not current_user:
        return jsonify({
            'status': 'error',
            'message': 'User not found'
        }), 404
    
    # Get query parameters
    store_id = request.args.get('store_id', type=int)
    
    # Build query
    query = db.session.query(
        InventoryEntry.payment_status,
        func.count(InventoryEntry.id).label('count'),
        func.sum(InventoryEntry.buying_price * InventoryEntry.quantity_received).label('total_amount')
    ).join(Product, InventoryEntry.product_id == Product.id)
    
    # Restrict to user's store if not merchant
    if current_user.role != UserRole.MERCHANT:
        query = query.filter(Product.store_id == current_user.store_id)
    elif store_id:
        query = query.filter(Product.store_id == store_id)
    
    # Group by payment status
    query = query.group_by(InventoryEntry.payment_status)
    
    # Execute query
    results = query.all()
    
    # Prepare response
    report_data = {
        'total_paid': 0.0,
        'total_unpaid': 0.0
    }
    for row in results:
        amount = float(row.total_amount) if row.total_amount else 0.0
        if row.payment_status == PaymentStatus.PAID:
            report_data['total_paid'] = amount
        else:
            report_data['total_unpaid'] = amount
    
    return jsonify({
        'status': 'success',
        'report': report_data
    }), 200