# routes/inventory.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func

from extensions import db
from models import (
    Product, InventoryEntry, SupplyRequest, User, 
    UserRole, RequestStatus, PaymentStatus, Store,
    Supplier, ProductCategory
)

inventory_bp = Blueprint('inventory', __name__)

# Helper function to check if user has specific role
def has_role(user_id, roles):
    user = db.session.get(User, user_id)  # Updated to use Session.get()
    return user and user.role in roles

@inventory_bp.route('/products', methods=['GET'])
@jwt_required()
def get_products():
    """Get products list with filters"""
    current_user_id = get_jwt_identity()['id']
    current_user = db.session.get(User, current_user_id)  # Updated to use Session.get()
    
    if not current_user:
        return jsonify({
            'status': 'error',
            'message': 'User not found'
        }), 404
    
    # Get query parameters
    category_id = request.args.get('category_id', type=int)
    store_id = request.args.get('store_id', type=int)
    low_stock = request.args.get('low_stock', type=bool, default=False)
    
    # Start with base query
    query = Product.query
    
    # Apply filters
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    # For non-merchant users, restrict to their store
    if current_user.role != UserRole.MERCHANT:
        query = query.filter_by(store_id=current_user.store_id)
    elif store_id:  # Merchant can filter by store
        query = query.filter_by(store_id=store_id)
    
    # Filter for low stock if requested
    if low_stock:
        query = query.filter(Product.current_stock <= Product.min_stock_level)
    
    # Execute query
    products = query.all()
    
    # Prepare response
    result = []
    for product in products:
        store = db.session.get(Store, product.store_id)  # Updated to use Session.get()
        category = None
        if product.category_id:
            category = db.session.get(ProductCategory, product.category_id)  # Updated to use Session.get()
        
        result.append({
            'id': product.id,
            'name': product.name,
            'sku': product.sku,
            'category_id': product.category_id,
            'category_name': category.name if category else None,
            'store_id': product.store_id,
            'store_name': store.name if store else None,
            'current_stock': product.current_stock,
            'min_stock_level': product.min_stock_level,
            'low_stock': product.current_stock <= product.min_stock_level,
            'created_at': product.created_at.isoformat(),
            'updated_at': product.updated_at.isoformat()
        })
    
    return jsonify({
        'status': 'success',
        'products': result
    }), 200

@inventory_bp.route('/products', methods=['POST'])
@jwt_required()
def create_product():
    """Create a new product"""
    current_user_id = get_jwt_identity()['id']
    current_user = db.session.get(User, current_user_id)  # Updated to use Session.get()
    
    if not current_user or current_user.role == UserRole.CLERK:
        return jsonify({
            'status': 'error',
            'message': 'Unauthorized to create products'
        }), 403
    
    data = request.get_json()
    
    if not data or not data.get('name') or not data.get('store_id'):
        return jsonify({
            'status': 'error',
            'message': 'Product name and store ID are required'
        }), 400
    
    # Admin can only create products for their store
    if current_user.role == UserRole.ADMIN and current_user.store_id != data['store_id']:
        return jsonify({
            'status': 'error',
            'message': 'You can only create products for your store'
        }), 403
    
    # Check if store exists
    store = db.session.get(Store, data['store_id'])  # Updated to use Session.get()
    if not store:
        return jsonify({
            'status': 'error',
            'message': 'Store not found'
        }), 404
    
    # Check category if provided
    category_id = data.get('category_id')
    if category_id:
        category = db.session.get(ProductCategory, category_id)  # Updated to use Session.get()
        if not category:
            return jsonify({
                'status': 'error',
                'message': 'Category not found'
            }), 404
    
    # Create product
    product = Product(
        name=data['name'],
        sku=data.get('sku'),
        category_id=category_id,
        store_id=data['store_id'],
        min_stock_level=data.get('min_stock_level', 5),
        current_stock=data.get('current_stock', 0)
    )
    
    db.session.add(product)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': 'Product created successfully',
        'product': {
            'id': product.id,
            'name': product.name,
            'sku': product.sku,
            'category_id': product.category_id,
            'store_id': product.store_id,
            'current_stock': product.current_stock,
            'min_stock_level': product.min_stock_level,
            'created_at': product.created_at.isoformat(),
            'updated_at': product.updated_at.isoformat()
        }
    }), 201

@inventory_bp.route('/entries', methods=['POST'])
@jwt_required()
def create_entry():
    """Create a new inventory entry"""
    current_user_id = get_jwt_identity()['id']
    current_user = db.session.get(User, current_user_id)  # Updated to use Session.get()
    
    if not current_user:
        return jsonify({
            'status': 'error',
            'message': 'User not found'
        }), 404
    
    data = request.get_json()
    
    if not data or not data.get('product_id') or not data.get('quantity_received') or \
       not data.get('buying_price') or not data.get('selling_price'):
        return jsonify({
            'status': 'error',
            'message': 'Product ID, quantity received, buying price, and selling price are required'
        }), 400
    
    # Validate product
    product = db.session.get(Product, data['product_id'])  # Updated to use Session.get()
    if not product:
        return jsonify({
            'status': 'error',
            'message': 'Product not found'
        }), 404
    
    # Clerk can only add entries for their store
    if current_user.store_id != product.store_id:
        return jsonify({
            'status': 'error',
            'message': 'You can only add entries for your store'
        }), 403
    
    # Validate supplier if provided
    supplier_id = data.get('supplier_id')
    if supplier_id:
        supplier = db.session.get(Supplier, supplier_id)  # Updated to use Session.get()
        if not supplier:
            return jsonify({
                'status': 'error',
                'message': 'Supplier not found'
            }), 404
    
    # Create entry
    entry = InventoryEntry(
        product_id=data['product_id'],
        quantity_received=data['quantity_received'],
        quantity_spoiled=data.get('quantity_spoiled', 0),
        buying_price=data['buying_price'],
        selling_price=data['selling_price'],
        payment_status=PaymentStatus[data.get('payment_status', 'UNPAID')],
        supplier_id=supplier_id,
        recorded_by=current_user_id
    )
    
    db.session.add(entry)
    
    # Update product stock
    net_quantity = data['quantity_received'] - data.get('quantity_spoiled', 0)
    product.current_stock += net_quantity
    
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': 'Inventory entry created successfully',
        'inventory_entry': {
            'id': entry.id,
            'product_id': entry.product_id,
            'quantity_received': entry.quantity_received,
            'quantity_spoiled': entry.quantity_spoiled,
            'buying_price': entry.buying_price,
            'selling_price': entry.selling_price,
            'payment_status': entry.payment_status.name,
            'supplier_id': entry.supplier_id,
            'recorded_by': entry.recorded_by,
            'entry_date': entry.entry_date.isoformat(),
            'created_at': entry.created_at.isoformat()
        }
    }), 201

@inventory_bp.route('/entries', methods=['GET'])
@jwt_required()
def get_entries():
    """Get inventory entries with filters"""
    current_user_id = get_jwt_identity()['id']
    current_user = db.session.get(User, current_user_id)  # Updated to use Session.get()
    
    if not current_user:
        return jsonify({
            'status': 'error',
            'message': 'User not found'
        }), 404
    
    # Get query parameters
    product_id = request.args.get('product_id', type=int)
    payment_status = request.args.get('payment_status')
    supplier_id = request.args.get('supplier_id', type=int)
    store_id = request.args.get('store_id', type=int)
    clerk_id = request.args.get('clerk_id', type=int)
    
    # Build query
    query = db.session.query(InventoryEntry, Product, User, Store).\
        join(Product, InventoryEntry.product_id == Product.id).\
        join(User, InventoryEntry.recorded_by == User.id).\
        join(Store, Product.store_id == Store.id)
    
    # Apply filters
    if product_id:
        query = query.filter(InventoryEntry.product_id == product_id)
    
    if payment_status:
        try:
            query = query.filter(InventoryEntry.payment_status == PaymentStatus[payment_status])
        except KeyError:
            return jsonify({
                'status': 'error',
                'message': 'Invalid payment status'
            }), 400
    
    if supplier_id:
        query = query.filter(InventoryEntry.supplier_id == supplier_id)
    
    if clerk_id:
        query = query.filter(InventoryEntry.recorded_by == clerk_id)
    
    # Non-merchant users can only see entries from their store
    if current_user.role != UserRole.MERCHANT:
        query = query.filter(Product.store_id == current_user.store_id)
    elif store_id:  # Merchant can filter by store
        query = query.filter(Product.store_id == store_id)
    
    # Execute query
    entries = query.all()
    
    # Prepare response
    result = []
    for entry, product, user, store in entries:
        supplier_name = None
        if entry.supplier_id:
            supplier = db.session.get(Supplier, entry.supplier_id)  # Updated to use Session.get()
            supplier_name = supplier.name if supplier else None
        
        result.append({
            'id': entry.id,
            'product_id': entry.product_id,
            'product_name': product.name,
            'quantity_received': entry.quantity_received,
            'quantity_spoiled': entry.quantity_spoiled,
            'buying_price': entry.buying_price,
            'selling_price': entry.selling_price,
            'payment_status': entry.payment_status.name,
            'supplier_id': entry.supplier_id,
            'supplier_name': supplier_name,
            'clerk_id': entry.recorded_by,
            'clerk_name': user.name,
            'store_id': store.id,
            'store_name': store.name,
            'entry_date': entry.entry_date.isoformat(),
            'created_at': entry.created_at.isoformat()
        })
    
    return jsonify({
        'status': 'success',
        'entries': result
    }), 200

@inventory_bp.route('/supply-requests', methods=['POST'])
@jwt_required()
def create_supply_request():
    """Create a new supply request"""
    current_user_id = get_jwt_identity()['id']
    current_user = db.session.get(User, current_user_id)  # Updated to use Session.get()
    
    if not current_user:
        return jsonify({
            'status': 'error',
            'message': 'User not found'
        }), 404
    
    data = request.get_json()
    
    if not data or not data.get('product_id') or not data.get('quantity_requested'):
        return jsonify({
            'status': 'error',
            'message': 'Product ID and quantity requested are required'
        }), 400
    
    # Validate product
    product = db.session.get(Product, data['product_id'])  # Updated to use Session.get()
    if not product:
        return jsonify({
            'status': 'error',
            'message': 'Product not found'
        }), 404
    
    # User can only request supplies for their store
    if current_user.store_id != product.store_id:
        return jsonify({
            'status': 'error',
            'message': 'You can only request supplies for your store'
        }), 403
    
    # Create request
    supply_request = SupplyRequest(
        product_id=data['product_id'],
        quantity_requested=data['quantity_requested'],
        clerk_id=current_user_id,
        status=RequestStatus.PENDING
    )
    
    db.session.add(supply_request)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': 'Supply request created successfully',
        'supply_request': {
            'id': supply_request.id,
            'product_id': supply_request.product_id,
            'quantity_requested': supply_request.quantity_requested,
            'clerk_id': supply_request.clerk_id,
            'status': supply_request.status.name,
            'created_at': supply_request.created_at.isoformat()
        }
    }), 201

@inventory_bp.route('/supply-requests', methods=['GET'])
@jwt_required()
def get_supply_requests():
    """Get supply requests with filters"""
    current_user_id = get_jwt_identity()['id']
    current_user = db.session.get(User, current_user_id)  # Updated to use Session.get()
    
    if not current_user:
        return jsonify({
            'status': 'error',
            'message': 'User not found'
        }), 404
    
    # Get query parameters
    product_id = request.args.get('product_id', type=int)
    status = request.args.get('status')
    clerk_id = request.args.get('clerk_id', type=int)
    store_id = request.args.get('store_id', type=int)
    
    # Build query
    query = db.session.query(SupplyRequest, Product, User, Store).\
        join(Product, SupplyRequest.product_id == Product.id).\
        join(User, SupplyRequest.clerk_id == User.id).\
        join(Store, Product.store_id == Store.id)
    
    # Apply filters
    if product_id:
        query = query.filter(SupplyRequest.product_id == product_id)
    
    if status:
        try:
            query = query.filter(SupplyRequest.status == RequestStatus[status])
        except KeyError:
            return jsonify({
                'status': 'error',
                'message': 'Invalid request status'
            }), 400
    
    if clerk_id:
        query = query.filter(SupplyRequest.clerk_id == clerk_id)
    
    # Non-merchant users can only see requests from their store
    if current_user.role != UserRole.MERCHANT:
        query = query.filter(Product.store_id == current_user.store_id)
    elif store_id:  # Merchant can filter by store
        query = query.filter(Product.store_id == store_id)
    
    # Clerk can only see their own requests
    if current_user.role == UserRole.CLERK:
        query = query.filter(SupplyRequest.clerk_id == current_user_id)
    
    # Execute query
    requests = query.all()
    
    # Prepare response
    result = []
    for req, product, user, store in requests:
        admin_name = None
        if req.admin_id:
            admin = db.session.get(User, req.admin_id)  # Updated to use Session.get()
            admin_name = admin.name if admin else None
        
        result.append({
            'id': req.id,
            'product_id': req.product_id,
            'product_name': product.name,
            'quantity_requested': req.quantity_requested,
            'clerk_id': req.clerk_id,
            'clerk_name': user.name,
            'status': req.status.name,
            'admin_id': req.admin_id,
            'admin_name': admin_name,
            'decline_reason': req.decline_reason,
            'store_id': store.id,
            'store_name': store.name,
            'created_at': req.created_at.isoformat()
        })
    
    return jsonify({
        'status': 'success',
        'requests': result
    }), 200

@inventory_bp.route('/supply-requests/<int:request_id>', methods=['PUT'])
@jwt_required()
def update_supply_request(request_id):
    """Update a supply request (approve/decline)"""
    current_user_id = get_jwt_identity()['id']
    current_user = db.session.get(User, current_user_id)  # Updated to use Session.get()
    
    if not current_user or current_user.role == UserRole.CLERK:
        return jsonify({
            'status': 'error',
            'message': 'Unauthorized to update supply requests'
        }), 403
    
    req = db.session.get(SupplyRequest, request_id)  # Updated to use Session.get()
    if not req:
        return jsonify({
            'status': 'error',
            'message': 'Supply request not found'
        }), 404
    
    # Check if request is from user's store
    product = db.session.get(Product, req.product_id)  # Updated to use Session.get()
    if not product or (current_user.role == UserRole.ADMIN and current_user.store_id != product.store_id):
        return jsonify({
            'status': 'error',
            'message': 'You can only update requests for your store'
        }), 403
    
    data = request.get_json()
    if not data or not data.get('status'):
        return jsonify({
            'status': 'error',
            'message': 'Status is required'
        }), 400
    
    # Update status
    try:
        new_status = RequestStatus[data['status']]
    except KeyError:
        return jsonify({
            'status': 'error',
            'message': 'Invalid status'
        }), 400
    
    # Only pending requests can be updated
    if req.status != RequestStatus.PENDING:
        return jsonify({
            'status': 'error',
            'message': 'Only pending requests can be updated'
        }), 400
    
    req.status = new_status
    req.admin_id = current_user_id
    
    if new_status == RequestStatus.DECLINED and data.get('decline_reason'):
        req.decline_reason = data['decline_reason']
    
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': f'Supply request {new_status.name.lower()} successfully',
        'supply_request': {
            'id': req.id,
            'product_id': req.product_id,
            'quantity_requested': req.quantity_requested,
            'clerk_id': req.clerk_id,
            'status': req.status.name,
            'admin_id': req.admin_id,
            'decline_reason': req.decline_reason,
            'created_at': req.created_at.isoformat()
        }
    }), 200

@inventory_bp.route('/supply-requests/<int:request_id>/approve', methods=['PUT'])
@jwt_required()
def approve_supply_request(request_id):
    """Approve a supply request"""
    current_user_id = get_jwt_identity()['id']
    current_user = db.session.get(User, current_user_id)  # Updated to use Session.get()
    
    if not current_user or current_user.role == UserRole.CLERK:
        return jsonify({
            'status': 'error',
            'message': 'Unauthorized to approve supply requests'
        }), 403
    
    req = db.session.get(SupplyRequest, request_id)  # Updated to use Session.get()
    if not req:
        return jsonify({
            'status': 'error',
            'message': 'Supply request not found'
        }), 404
    
    # Check if request is from user's store
    product = db.session.get(Product, req.product_id)  # Updated to use Session.get()
    if not product or (current_user.role == UserRole.ADMIN and current_user.store_id != product.store_id):
        return jsonify({
            'status': 'error',
            'message': 'You can only approve requests for your store'
        }), 403
    
    # Only pending requests can be approved
    if req.status != RequestStatus.PENDING:
        return jsonify({
            'status': 'error',
            'message': 'Only pending requests can be approved'
        }), 400
    
    req.status = RequestStatus.APPROVED
    req.admin_id = current_user_id
    
    db.session.commit()
    
    return jsonify({
        'status': 'success',