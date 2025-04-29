from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func
import logging
import os

from extensions import db, socketio, cache  # Added socketio and cache imports
from models import (
    Product, InventoryEntry, SupplyRequest, User, 
    UserRole, RequestStatus, PaymentStatus, Store,
    Supplier, ProductCategory, Notification
)
from schemas import ProductSchema, InventoryEntrySchema, SupplyRequestSchema

inventory_bp = Blueprint('inventory', __name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Helper function to check if user has specific role
def has_role(user_id, roles):
    user = db.session.get(User, user_id)
    return user and user.role in roles

# Helper function for pagination
def paginate_query(query, page=1, per_page=20):
    """Paginate SQLAlchemy query results"""
    return query.paginate(page=page, per_page=per_page, error_out=False)

# Validation constants from environment variables
MAX_QUANTITY = int(os.getenv('MAX_QUANTITY', 10000))
MAX_PRICE = int(os.getenv('MAX_PRICE', 1000000))

@inventory_bp.route('/products', methods=['GET'])
@jwt_required()
@cache.cached(timeout=60, query_string=True)  # Cache for 1 minute
def get_products():
    """
    Get a list of products with optional filters and pagination.
    
    Query Parameters:
        - category_id (int, optional): Filter by category ID
        - store_id (int, optional): Filter by store ID (for Merchants)
        - low_stock (bool, optional): Filter products below minimum stock level
        - page (int, optional): Page number (default 1)
        - per_page (int, optional): Items per page (default 20)
    
    Responses:
        - 200: List of products with pagination metadata
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
        
        category_id = request.args.get('category_id', type=int)
        store_id = request.args.get('store_id', type=int)
        low_stock = request.args.get('low_stock', type=bool, default=False)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        query = Product.query
        
        if category_id:
            query = query.filter_by(category_id=category_id)
        
        if current_user.role != UserRole.MERCHANT:
            query = query.filter_by(store_id=current_user.store_id)
        elif store_id:
            query = query.filter_by(store_id=store_id)
        
        if low_stock:
            query = query.filter(Product.current_stock <= Product.min_stock_level)
        
        # Apply pagination
        paginated_products = paginate_query(query, page, per_page)
        
        # Use ProductSchema to serialize the products
        product_schema = ProductSchema(many=True)
        result = product_schema.dump(paginated_products.items)
        
        # Add additional fields like category_name and store_name
        for product, serialized in zip(paginated_products.items, result):
            store = db.session.get(Store, product.store_id)
            category = None
            if product.category_id:
                category = db.session.get(ProductCategory, product.category_id)
            serialized['category_name'] = category.name if category else None
            serialized['store_name'] = store.name if store else None
            serialized['low_stock'] = product.current_stock <= product.min_stock_level
        
        return jsonify({
            'status': 'success',
            'products': result,
            'total': paginated_products.total,
            'pages': paginated_products.pages,
            'current_page': paginated_products.page
        }), 200
    except Exception as e:
        logger.error(f"Error in get_products: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

@inventory_bp.route('/products', methods=['POST'])
@jwt_required()
def create_product():
    """
    Create a new product.
    
    Request Body:
        - name (str): Product name
        - store_id (int): Store ID
        - category_id (int, optional): Category ID
        - min_stock_level (int, optional): Minimum stock level (default 5)
        - current_stock (int, optional): Initial stock (default 0)
    
    Responses:
        - 201: Product created successfully
        - 400: Invalid input
        - 403: Unauthorized to create products
        - 404: Store or category not found
        - 500: Internal server error
    """
    try:
        current_user_id = get_jwt_identity()['id']
        current_user = db.session.get(User, current_user_id)
        
        if not current_user or current_user.role == UserRole.CLERK:
            return jsonify({
                'status': 'error',
                'message': 'Unauthorized to create products'
            }), 403
        
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Request body is required'
            }), 400
        
        # Validate request data using ProductSchema
        product_schema = ProductSchema()
        errors = product_schema.validate(data)
        if errors:
            return jsonify({
                'status': 'error',
                'message': 'Validation error',
                'errors': errors
            }), 400
        
        if current_user.role == UserRole.ADMIN and current_user.store_id != data['store_id']:
            return jsonify({
                'status': 'error',
                'message': 'You can only create products for your store'
            }), 403
        
        store = db.session.get(Store, data['store_id'])
        if not store:
            return jsonify({
                'status': 'error',
                'message': 'Store not found'
            }), 404
        
        category_id = data.get('category_id')
        if category_id:
            category = db.session.get(ProductCategory, category_id)
            if not category:
                return jsonify({
                    'status': 'error',
                    'message': 'Category not found'
                }), 404
        
        product = Product(
            name=data['name'],
            sku=data.get('sku'),
            category_id=category_id,
            store_id=data['store_id'],
            min_stock_level=data.get('min_stock_level', 5),
            current_stock=data.get('current_stock', 0)
        )
        
        db.session.add(product)
        db.session.flush()
        
        # Notify Admins and Merchants if the initial stock is low
        if product.current_stock <= product.min_stock_level:
            users_to_notify = User.query.filter(
                User.store_id == product.store_id,
                User.role.in_([UserRole.ADMIN, UserRole.MERCHANT])
            ).all()
            for user in users_to_notify:
                notification = Notification(
                    user_id=user.id,
                    message=f"New product '{product.name}' added with low stock: {product.current_stock} units."
                )
                db.session.add(notification)
                db.session.flush()
                # Emit WebSocket event
                socketio.emit('new_notification', {
                    'id': notification.id,
                    'message': notification.message,
                    'created_at': notification.created_at.isoformat()
                }, room=f'user_{user.id}')
        
        db.session.commit()
        
        # Serialize the created product
        serialized_product = product_schema.dump(product)
        
        logger.info(f"Product created: {product.name} (ID: {product.id}) by user ID: {current_user_id}")
        return jsonify({
            'status': 'success',
            'message': 'Product created successfully',
            'product': serialized_product
        }), 201
    except Exception as e:
        logger.error(f"Error in create_product: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

@inventory_bp.route('/entries', methods=['POST'])
@jwt_required()
def create_entry():
    """
    Create a new inventory entry and update product stock.
    
    Request Body:
        - product_id (int): Product ID
        - quantity_received (int): Quantity received
        - buying_price (float): Buying price per unit
        - selling_price (float): Selling price per unit
        - quantity_spoiled (int, optional): Quantity spoiled (default 0)
        - payment_status (str, optional): Payment status (default 'UNPAID')
        - supplier_id (int, optional): Supplier ID
    
    Responses:
        - 201: Inventory entry created successfully
        - 400: Invalid input
        - 403: Unauthorized to add entries
        - 404: Product or supplier not found
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
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Request body is required'
            }), 400
        
        # Validate request data using InventoryEntrySchema
        entry_schema = InventoryEntrySchema()
        errors = entry_schema.validate(data)
        if errors:
            return jsonify({
                'status': 'error',
                'message': 'Validation error',
                'errors': errors
            }), 400
        
        product = db.session.get(Product, data['product_id'])
        if not product:
            return jsonify({
                'status': 'error',
                'message': 'Product not found'
            }), 404
        
        if current_user.store_id != product.store_id:
            return jsonify({
                'status': 'error',
                'message': 'You can only add entries for your store'
            }), 403
        
        supplier_id = data.get('supplier_id')
        if supplier_id:
            supplier = db.session.get(Supplier, supplier_id)
            if not supplier:
                return jsonify({
                    'status': 'error',
                    'message': 'Supplier not found'
                }), 404
        
        # Use a transaction to ensure consistency
        with db.session.begin_nested():
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
            
            net_quantity = entry.quantity_received - entry.quantity_spoiled
            product.current_stock += net_quantity
            
            db.session.flush()
            
            # Notify if stock is low after the update
            if product.current_stock <= product.min_stock_level:
                users_to_notify = User.query.filter(
                    User.store_id == product.store_id,
                    User.role.in_([UserRole.ADMIN, UserRole.MERCHANT])
                ).all()
                for user in users_to_notify:
                    notification = Notification(
                        user_id=user.id,
                        message=f"Product '{product.name}' stock is low: {product.current_stock} units."
                    )
                    db.session.add(notification)
                    db.session.flush()
                    # Emit WebSocket event
                    socketio.emit('new_notification', {
                        'id': notification.id,
                        'message': notification.message,
                        'created_at': notification.created_at.isoformat()
                    }, room=f'user_{user.id}')
        
        db.session.commit()
        
        # Serialize the created entry
        serialized_entry = entry_schema.dump(entry)
        
        logger.info(f"Inventory entry created for product: {product.name} (ID: {entry.id}) by user ID: {current_user_id}")
        return jsonify({
            'status': 'success',
            'message': 'Inventory entry created successfully',
            'inventory_entry': serialized_entry
        }), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in create_entry: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

@inventory_bp.route('/entries/<int:entry_id>', methods=['PUT'])
@jwt_required()
def update_entry(entry_id):
    """
    Update an existing inventory entry and adjust product stock accordingly.
    
    Request Body:
        - quantity_received (int, optional): Updated quantity received
        - quantity_spoiled (int, optional): Updated quantity spoiled
        - buying_price (float, optional): Updated buying price
        - selling_price (float, optional): Updated selling price
        - payment_status (str, optional): Updated payment status
        - supplier_id (int, optional): Updated supplier ID
    
    Responses:
        - 200: Inventory entry updated successfully
        - 400: Invalid input
        - 403: Unauthorized to update entries
        - 404: Entry, product, or supplier not found
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
        
        if current_user.role == UserRole.CLERK:
            return jsonify({
                'status': 'error',
                'message': 'Unauthorized to update inventory entries'
            }), 403
        
        entry = db.session.get(InventoryEntry, entry_id)
        if not entry:
            return jsonify({
                'status': 'error',
                'message': 'Inventory entry not found'
            }), 404
        
        product = db.session.get(Product, entry.product_id)
        if not product or (current_user.role == UserRole.ADMIN and current_user.store_id != product.store_id):
            return jsonify({
                'status': 'error',
                'message': 'You can only update entries for your store'
            }), 403
        
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No data provided for update'
            }), 400
        
        # Validate request data using InventoryEntrySchema (partial validation)
        entry_schema = InventoryEntrySchema(partial=True)
        errors = entry_schema.validate(data)
        if errors:
            return jsonify({
                'status': 'error',
                'message': 'Validation error',
                'errors': errors
            }), 400
        
        # Use a transaction to ensure consistency
        with db.session.begin_nested():
            # Revert the previous stock change
            previous_net_quantity = entry.quantity_received - entry.quantity_spoiled
            product.current_stock -= previous_net_quantity
            
            # Update fields if provided
            if 'quantity_received' in data:
                entry.quantity_received = data['quantity_received']
            
            if 'quantity_spoiled' in data:
                if data['quantity_spoiled'] > entry.quantity_received:
                    return jsonify({
                        'status': 'error',
                        'message': 'Quantity spoiled must be less than quantity received'
                    }), 400
                entry.quantity_spoiled = data['quantity_spoiled']
            
            if 'buying_price' in data:
                entry.buying_price = data['buying_price']
            
            if 'selling_price' in data:
                entry.selling_price = data['selling_price']
            
            if 'payment_status' in data:
                try:
                    entry.payment_status = PaymentStatus[data['payment_status']]
                except KeyError:
                    return jsonify({
                        'status': 'error',
                        'message': 'Invalid payment status'
                    }), 400
            
            if 'supplier_id' in data:
                supplier_id = data['supplier_id']
                if supplier_id:
                    supplier = db.session.get(Supplier, supplier_id)
                    if not supplier:
                        return jsonify({
                            'status': 'error',
                            'message': 'Supplier not found'
                        }), 404
                entry.supplier_id = supplier_id
            
            # Apply the new stock change
            new_net_quantity = entry.quantity_received - entry.quantity_spoiled
            product.current_stock += new_net_quantity
            
            db.session.flush()
            
            # Notify if stock is low after the update
            if product.current_stock <= product.min_stock_level:
                users_to_notify = User.query.filter(
                    User.store_id == product.store_id,
                    User.role.in_([UserRole.ADMIN, UserRole.MERCHANT])
                ).all()
                for user in users_to_notify:
                    notification = Notification(
                        user_id=user.id,
                        message=f"Product '{product.name}' stock updated to low level: {product.current_stock} units."
                    )
                    db.session.add(notification)
                    db.session.flush()
                    # Emit WebSocket event
                    socketio.emit('new_notification', {
                        'id': notification.id,
                        'message': notification.message,
                        'created_at': notification.created_at.isoformat()
                    }, room=f'user_{user.id}')
        
        db.session.commit()
        
        # Serialize the updated entry
        serialized_entry = entry_schema.dump(entry)
        
        logger.info(f"Inventory entry updated: {entry.id} by user ID: {current_user_id}")
        return jsonify({
            'status': 'success',
            'message': 'Inventory entry updated successfully',
            'inventory_entry': serialized_entry
        }), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in update_entry: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

@inventory_bp.route('/entries/<int:entry_id>', methods=['DELETE'])
@jwt_required()
def delete_entry(entry_id):
    """
    Delete an inventory entry and adjust product stock accordingly.
    
    Responses:
        - 200: Inventory entry deleted successfully
        - 403: Unauthorized to delete entries
        - 404: Entry or product not found
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
        
        if current_user.role == UserRole.CLERK:
            return jsonify({
                'status': 'error',
                'message': 'Unauthorized to delete inventory entries'
            }), 403
        
        entry = db.session.get(InventoryEntry, entry_id)
        if not entry:
            return jsonify({
                'status': 'error',
                'message': 'Inventory entry not found'
            }), 404
        
        product = db.session.get(Product, entry.product_id)
        if not product or (current_user.role == UserRole.ADMIN and current_user.store_id != product.store_id):
            return jsonify({
                'status': 'error',
                'message': 'You can only delete entries for your store'
            }), 403
        
        # Use a transaction to ensure consistency
        with db.session.begin_nested():
            # Revert the stock change
            net_quantity = entry.quantity_received - entry.quantity_spoiled
            product.current_stock -= net_quantity
            
            # Delete the entry
            db.session.delete(entry)
            
            db.session.flush()
            
            # Notify if stock is low after the deletion
            if product.current_stock <= product.min_stock_level:
                users_to_notify = User.query.filter(
                    User.store_id == product.store_id,
                    User.role.in_([UserRole.ADMIN, UserRole.MERCHANT])
                ).all()
                for user in users_to_notify:
                    notification = Notification(
                        user_id=user.id,
                        message=f"Product '{product.name}' stock updated to low level: {product.current_stock} units after entry deletion."
                    )
                    db.session.add(notification)
                    db.session.flush()
                    # Emit WebSocket event
                    socketio.emit('new_notification', {
                        'id': notification.id,
                        'message': notification.message,
                        'created_at': notification.created_at.isoformat()
                    }, room=f'user_{user.id}')
        
        db.session.commit()
        
        logger.info(f"Inventory entry deleted: {entry_id} by user ID: {current_user_id}")
        return jsonify({
            'status': 'success',
            'message': 'Inventory entry deleted successfully'
        }), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in delete_entry: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

@inventory_bp.route('/entries', methods=['GET'])
@jwt_required()
def get_entries():
    """
    Get inventory entries with optional filters and pagination.
    
    Query Parameters:
        - product_id (int, optional): Filter by product ID
        - payment_status (str, optional): Filter by payment status
        - supplier_id (int, optional): Filter by supplier ID
        - store_id (int, optional): Filter by store ID (for Merchants)
        - clerk_id (int, optional): Filter by clerk ID
        - page (int, optional): Page number (default 1)
        - per_page (int, optional): Items per page (default 20)
    
    Responses:
        - 200: List of inventory entries with pagination metadata
        - 400: Invalid payment status
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
        
        product_id = request.args.get('product_id', type=int)
        payment_status = request.args.get('payment_status')
        supplier_id = request.args.get('supplier_id', type=int)
        store_id = request.args.get('store_id', type=int)
        clerk_id = request.args.get('clerk_id', type=int)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        query = db.session.query(InventoryEntry, Product, User, Store).\
            join(Product, InventoryEntry.product_id == Product.id).\
            join(User, InventoryEntry.recorded_by == User.id).\
            join(Store, Product.store_id == Store.id)
        
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
        
        if current_user.role != UserRole.MERCHANT:
            query = query.filter(Product.store_id == current_user.store_id)
        elif store_id:
            query = query.filter(Product.store_id == store_id)
        
        # Apply pagination
        paginated_entries = paginate_query(query, page, per_page)
        
        # Use InventoryEntrySchema to serialize the entries
        entry_schema = InventoryEntrySchema(many=True)
        result = entry_schema.dump([entry for entry, _, _, _ in paginated_entries.items])
        
        # Add additional fields like product_name, clerk_name, etc.
        for (entry, product, user, store), serialized in zip(paginated_entries.items, result):
            supplier_name = None
            if entry.supplier_id:
                supplier = db.session.get(Supplier, entry.supplier_id)
                supplier_name = supplier.name if supplier else None
            serialized['product_name'] = product.name
            serialized['supplier_name'] = supplier_name
            serialized['clerk_id'] = entry.recorded_by
            serialized['clerk_name'] = user.name
            serialized['store_id'] = store.id
            serialized['store_name'] = store.name
            serialized['entry_date'] = entry.entry_date.isoformat()
        
        return jsonify({
            'status': 'success',
            'entries': result,
            'total': paginated_entries.total,
            'pages': paginated_entries.pages,
            'current_page': paginated_entries.page
        }), 200
    except Exception as e:
        logger.error(f"Error in get_entries: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

@inventory_bp.route('/supply-requests', methods=['POST'])
@jwt_required()
def create_supply_request():
    """
    Create a new supply request.
    
    Request Body:
        - product_id (int): Product ID
        - quantity_requested (int): Quantity requested
    
    Responses:
        - 201: Supply request created successfully
        - 400: Invalid input
        - 403: Unauthorized to request supplies
        - 404: Product or user not found
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
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Request body is required'
            }), 400
        
        # Validate request data using SupplyRequestSchema
        request_schema = SupplyRequestSchema()
        errors = request_schema.validate(data)
        if errors:
            return jsonify({
                'status': 'error',
                'message': 'Validation error',
                'errors': errors
            }), 400
        
        product = db.session.get(Product, data['product_id'])
        if not product:
            return jsonify({
                'status': 'error',
                'message': 'Product not found'
            }), 404
        
        if current_user.store_id != product.store_id:
            return jsonify({
                'status': 'error',
                'message': 'You can only request supplies for your store'
            }), 403
        
        supply_request = SupplyRequest(
            product_id=data['product_id'],
            quantity_requested=data['quantity_requested'],
            clerk_id=current_user_id,
            status=RequestStatus.PENDING
        )
        
        db.session.add(supply_request)
        db.session.commit()
        
        # Serialize the created supply request
        serialized_request = request_schema.dump(supply_request)
        serialized_request['clerk_id'] = supply_request.clerk_id
        
        logger.info(f"Supply request created for product: {product.name} (ID: {supply_request.id}) by user ID: {current_user_id}")
        return jsonify({
            'status': 'success',
            'message': 'Supply request created successfully',
            'supply_request': serialized_request
        }), 201
    except Exception as e:
        logger.error(f"Error in create_supply_request: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

@inventory_bp.route('/supply-requests', methods=['GET'])
@jwt_required()
def get_supply_requests():
    """
    Get supply requests with optional filters and pagination.
    
    Query Parameters:
        - product_id (int, optional): Filter by product ID
        - status (str, optional): Filter by request status
        - clerk_id (int, optional): Filter by clerk ID
        - store_id (int, optional): Filter by store ID (for Merchants)
        - page (int, optional): Page number (default 1)
        - per_page (int, optional): Items per page (default 20)
    
    Responses:
        - 200: List of supply requests with pagination metadata
        - 400: Invalid request status
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
        
        product_id = request.args.get('product_id', type=int)
        status = request.args.get('status')
        clerk_id = request.args.get('clerk_id', type=int)
        store_id = request.args.get('store_id', type=int)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        query = db.session.query(SupplyRequest, Product, User, Store).\
            join(Product, SupplyRequest.product_id == Product.id).\
            join(User, SupplyRequest.clerk_id == User.id).\
            join(Store, Product.store_id == Store.id)
        
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
        
        if current_user.role != UserRole.MERCHANT:
            query = query.filter(Product.store_id == current_user.store_id)
        elif store_id:
            query = query.filter(Product.store_id == store_id)
        
        if current_user.role == UserRole.CLERK:
            query = query.filter(SupplyRequest.clerk_id == current_user_id)
        
        # Apply pagination
        paginated_requests = paginate_query(query, page, per_page)
        
        # Use SupplyRequestSchema to serialize the requests
        request_schema = SupplyRequestSchema(many=True)
        result = request_schema.dump([req for req, _, _, _ in paginated_requests.items])
        
        # Add additional fields like product_name, clerk_name, etc.
        for (req, product, user, store), serialized in zip(paginated_requests.items, result):
            admin_name = None
            if req.admin_id:
                admin = db.session.get(User, req.admin_id)
                admin_name = admin.name if admin else None
            serialized['product_name'] = product.name
            serialized['clerk_id'] = req.clerk_id
            serialized['clerk_name'] = user.name
            serialized['admin_name'] = admin_name
            serialized['store_id'] = store.id
            serialized['store_name'] = store.name
        
        return jsonify({
            'status': 'success',
            'requests': result,
            'total': paginated_requests.total,
            'pages': paginated_requests.pages,
            'current_page': paginated_requests.page
        }), 200
    except Exception as e:
        logger.error(f"Error in get_supply_requests: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

@inventory_bp.route('/supply-requests/<int:request_id>', methods=['PUT'])
@jwt_required()
def update_supply_request(request_id):
    """
    Update a supply request (approve/decline).
    
    Request Body:
        - status (str): New status (APPROVED or DECLINED)
        - decline_reason (str, optional): Reason for declining (required if status is DECLINED)
    
    Responses:
        - 200: Supply request updated successfully
        - 400: Invalid input or request not pending
        - 403: Unauthorized to update requests
        - 404: Request or product not found
        - 500: Internal server error
    """
    try:
        current_user_id = get_jwt_identity()['id']
        current_user = db.session.get(User, current_user_id)
        
        if not current_user or current_user.role == UserRole.CLERK:
            return jsonify({
                'status': 'error',
                'message': 'Unauthorized to update supply requests'
            }), 403
        
        req = db.session.get(SupplyRequest, request_id)
        if not req:
            return jsonify({
                'status': 'error',
                'message': 'Supply request not found'
            }), 404
        
        product = db.session.get(Product, req.product_id)
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
        
        try:
            new_status = RequestStatus[data['status']]
        except KeyError:
            return jsonify({
                'status': 'error',
                'message': 'Invalid status'
            }), 400
        
        if req.status != RequestStatus.PENDING:
            return jsonify({
                'status': 'error',
                'message': 'Only pending requests can be updated'
            }), 400
        
        req.status = new_status
        req.admin_id = current_user_id
        
        if new_status == RequestStatus.DECLINED and data.get('decline_reason'):
            req.decline_reason = data['decline_reason']
        
        # Create a notification for the Clerk
        clerk = db.session.get(User, req.clerk_id)
        message = f"Your supply request for {product.name} has been {new_status.name.lower()}"
        if new_status == RequestStatus.DECLINED and req.decline_reason:
            message += f". Reason: {req.decline_reason}"
        notification = Notification(
            user_id=clerk.id,
            message=message
        )
        db.session.add(notification)
        db.session.flush()
        
        # Emit WebSocket event
        socketio.emit('new_notification', {
            'id': notification.id,
            'message': notification.message,
            'created_at': notification.created_at.isoformat()
        }, room=f'user_{clerk.id}')
        
        db.session.commit()
        
        # Serialize the updated supply request
        request_schema = SupplyRequestSchema()
        serialized_request = request_schema.dump(req)
        serialized_request['admin_id'] = req.admin_id
        serialized_request['decline_reason'] = req.decline_reason
        
        logger.info(f"Supply request {request_id} updated to {new_status.name} by user ID: {current_user_id}")
        return jsonify({
            'status': 'success',
            'message': f'Supply request {new_status.name.lower()} successfully',
            'supply_request': serialized_request
        }), 200
    except Exception as e:
        logger.error(f"Error in update_supply_request: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

@inventory_bp.route('/supply-requests/<int:request_id>/approve', methods=['PUT'])
@jwt_required()
def approve_supply_request(request_id):
    """
    Approve a supply request.
    
    Responses:
        - 200: Supply request approved successfully
        - 400: Request not pending
        - 403: Unauthorized to approve requests
        - 404: Request or product not found
        - 500: Internal server error
    """
    try:
        current_user_id = get_jwt_identity()['id']
        current_user = db.session.get(User, current_user_id)
        
        if not current_user or current_user.role == UserRole.CLERK:
            return jsonify({
                'status': 'error',
                'message': 'Unauthorized to approve supply requests'
            }), 403
        
        req = db.session.get(SupplyRequest, request_id)
        if not req:
            return jsonify({
                'status': 'error',
                'message': 'Supply request not found'
            }), 404
        
        product = db.session.get(Product, req.product_id)
        if not product or (current_user.role == UserRole.ADMIN and current_user.store_id != product.store_id):
            return jsonify({
                'status': 'error',
                'message': 'You can only approve requests for your store'
            }), 403
        
        if req.status != RequestStatus.PENDING:
            return jsonify({
                'status': 'error',
                'message': 'Only pending requests can be approved'
            }), 400
        
        with db.session.begin_nested():
            req.status = RequestStatus.APPROVED
            req.admin_id = current_user_id
            
            # Create a notification for the Clerk
            clerk = db.session.get(User, req.clerk_id)
            message = f"Your supply request for {product.name} has been approved"
            notification = Notification(
                user_id=clerk.id,
                message=message
            )
            db.session.add(notification)
            db.session.flush()
            
            # Emit WebSocket event
            socketio.emit('new_notification', {
                'id': notification.id,
                'message': notification.message,
                'created_at': notification.created_at.isoformat()
            }, room=f'user_{clerk.id}')
        
        db.session.commit()
        
        # Serialize the updated supply request
        request_schema = SupplyRequestSchema()
        serialized_request = request_schema.dump(req)
        serialized_request['admin_id'] = req.admin_id
        serialized_request['decline_reason'] = req.decline_reason
        
        logger.info(f"Supply request {request_id} approved by user ID: {current_user_id}")
        return jsonify({
            'status': 'success',
            'message': 'Supply request approved successfully',
            'supply_request': serialized_request
        }), 200
    except Exception as e:
        logger.error(f"Error in approve_supply_request: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

@inventory_bp.route('/update-payment/<int:entry_id>', methods=['PUT'])
@jwt_required()
def update_payment_status(entry_id):
    """
    Update the payment status of an inventory entry.
    
    Request Body:
        - payment_status (str): New payment status
    
    Responses:
        - 200: Payment status updated successfully
        - 400: Invalid input
        - 403: Unauthorized to update payment status
        - 404: Entry or product not found
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
        
        if current_user.role == UserRole.CLERK:
            return jsonify({
                'status': 'error',
                'message': 'Unauthorized to update payment status'
            }), 403
        
        data = request.get_json()
        if not data or not data.get('payment_status'):
            return jsonify({
                'status': 'error',
                'message': 'Payment status is required'
            }), 400
        
        try:
            new_status = PaymentStatus[data['payment_status']]
        except KeyError:
            return jsonify({
                'status': 'error',
                'message': 'Invalid payment status'
            }), 400
        
        entry = db.session.get(InventoryEntry, entry_id)
        if not entry:
            return jsonify({
                'status': 'error',
                'message': 'Inventory entry not found'
            }), 404
        
        product = db.session.get(Product, entry.product_id)
        if not product or (current_user.role == UserRole.ADMIN and current_user.store_id != product.store_id):
            return jsonify({
                'status': 'error',
                'message': 'You can only update entries for your store'
            }), 403
        
        entry.payment_status = new_status
        
        # Notify the recorded user if payment status changes
        recorded_user = db.session.get(User, entry.recorded_by)
        if recorded_user:
            notification = Notification(
                user_id=recorded_user.id,
                message=f"Payment status for inventory entry of product '{product.name}' updated to {new_status.name}."
            )
            db.session.add(notification)
            db.session.flush()
            # Emit WebSocket event
            socketio.emit('new_notification', {
                'id': notification.id,
                'message': notification.message,
                'created_at': notification.created_at.isoformat()
            }, room=f'user_{recorded_user.id}')
        
        db.session.commit()
        
        # Serialize the updated entry
        entry_schema = InventoryEntrySchema()
        serialized_entry = entry_schema.dump(entry)
        
        logger.info(f"Payment status updated for entry {entry_id} to {new_status.name} by user ID: {current_user_id}")
        return jsonify({
            'status': 'success',
            'message': 'Payment status updated successfully',
            'inventory_entry': serialized_entry
        }), 200
    except Exception as e:
        logger.error(f"Error in update_payment_status: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

@inventory_bp.route('/low-stock', methods=['GET'])
@jwt_required()
def low_stock():
    """
    Get products below minimum stock level for the user's store (accessible to Clerks, Admins, and Merchants).
    Consolidated endpoint replacing '/alerts/low-stock' and '/low-stock'.
    
    Responses:
        - 200: List of low stock products
        - 403: Unauthorized (for Clerks trying to access '/alerts/low-stock')
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
        
        query = db.session.query(Product, Store).\
            join(Store, Product.store_id == Store.id).\
            filter(Product.current_stock <= Product.min_stock_level)
        
        if current_user.role in [UserRole.CLERK, UserRole.ADMIN]:
            query = query.filter(Product.store_id == current_user.store_id)
        
        products = query.all()
        
        # Use ProductSchema to serialize the products
        product_schema = ProductSchema(many=True)
        result = product_schema.dump([product for product, _ in products])
        
        # Add additional fields like store_name, category_name
        for (product, store), serialized in zip(products, result):
            category = None
            if product.category_id:
                category = db.session.get(ProductCategory, product.category_id)
            serialized['product_id'] = product.id
            serialized['product_name'] = product.name
            serialized['store_name'] = store.name
            serialized['category_name'] = category.name if category else None
        
        logger.info(f"Low stock products retrieved by user ID: {current_user_id}")
        return jsonify({
            'status': 'success',
            'low_stock_products': result
        }), 200
    except Exception as e:
        logger.error(f"Error in low_stock: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

@inventory_bp.route('/suppliers/unpaid', methods=['GET'])
@jwt_required()
def unpaid_suppliers():
    """
    Get all unpaid inventory entries with supplier details.
    
    Responses:
        - 200: List of unpaid entries
        - 403: Unauthorized to view unpaid suppliers
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
        
        if current_user.role == UserRole.CLERK:
            return jsonify({
                'status': 'error',
                'message': 'Unauthorized to view unpaid suppliers'
            }), 403
        
        query = db.session.query(InventoryEntry, Product, Supplier, Store).\
            join(Product, InventoryEntry.product_id == Product.id).\
            join(Supplier, InventoryEntry.supplier_id == Supplier.id).\
            join(Store, Product.store_id == Store.id).\
            filter(InventoryEntry.payment_status == PaymentStatus.UNPAID)
        
        if current_user.role == UserRole.ADMIN:
            query = query.filter(Product.store_id == current_user.store_id)
        
        entries = query.all()
        
        # Use InventoryEntrySchema to serialize the entries
        entry_schema = InventoryEntrySchema(many=True)
        result = entry_schema.dump([entry for entry, _, _, _ in entries])
        
        # Add additional fields like product_name, supplier_name, etc.
        for (entry, product, supplier, store), serialized in zip(entries, result):
            serialized['entry_id'] = entry.id
            serialized['product_name'] = product.name
            serialized['total_amount'] = entry.quantity_received * entry.buying_price
            serialized['supplier_name'] = supplier.name
            serialized['supplier_email'] = supplier.email
            serialized['store_name'] = store.name
            serialized['entry_date'] = entry.entry_date.isoformat()
        
        logger.info(f"Unpaid suppliers retrieved by user ID: {current_user_id}")
        return jsonify({
            'status': 'success',
            'unpaid_entries': result
        }), 200
    except Exception as e:
        logger.error(f"Error in unpaid_suppliers: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

@inventory_bp.route('/products/search', methods=['GET'])
@jwt_required()
def search_products():
    """
    Search products by name or category.
    
    Query Parameters:
        - q (str): Search term
    
    Responses:
        - 200: List of matching products
        - 400: Search term required
        - 403: Unauthorized
        - 404: User not found
        - 500: Internal server error
    """
    try:
        current_user_id = get_jwt_identity()['id']
        current_user = db.session.get(User, current_user_id)
        
        if not current_user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
        search_term = request.args.get('q', '').strip()
        if not search_term:
            return jsonify({'status': 'error', 'message': 'Search term required'}), 400
        
        query = Product.query.join(ProductCategory).filter(
            db.or_(
                Product.name.ilike(f'%{search_term}%'),
                ProductCategory.name.ilike(f'%{search_term}%')
            )
        )
        
        if current_user.role != UserRole.MERCHANT:
            query = query.filter(Product.store_id == current_user.store_id)
        
        products = query.limit(50).all()
        
        product_schema = ProductSchema(many=True)
        result = product_schema.dump(products)
        
        return jsonify({
            'status': 'success',
            'products': result,
            'count': len(result)
        }), 200
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Search failed'}), 500