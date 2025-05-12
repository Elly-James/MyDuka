from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
import logging

from extensions import db, socketio
from models import (
    Product, InventoryEntry, Supplier, SupplyRequest, User, Store,
    UserRole, PaymentStatus, RequestStatus, ProductCategory, Notification, user_store, ActivityLog, NotificationType
)
from schemas import ProductSchema, InventoryEntrySchema, SupplierSchema, SupplyRequestSchema

inventory_bp = Blueprint('inventory', __name__, url_prefix='/api/inventory')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

def get_period_dates(period):
    """Helper function to get date ranges for reporting periods, aligned with reports.py."""
    today = datetime.utcnow().replace(hour=23, minute=59, second=59, microsecond=999999)
    if period == 'weekly':
        start = today - timedelta(days=7)
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = today
    elif period == 'monthly':
        start = today - timedelta(days=30)
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = today
    else:  # Default to weekly
        start = today - timedelta(days=7)
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = today
    return start, end

@inventory_bp.route('/products', methods=['GET', 'POST'])
@jwt_required()
def manage_products():
    """
    GET: List all products with filtering and pagination.
    POST: Create a new product.
    Query Parameters (GET):
        - category_id (int, optional): Filter by category ID
        - store_id (int, optional): Filter by store ID
        - low_stock (bool, optional): Filter by low stock status
        - search (str, optional): Search by product name
        - page (int, optional): Page number (default 1)
        - per_page (int, optional): Items per page (default 20)
    Request Body (POST):
        - name (str): Product name
        - store_id (int): Store ID
        - category_id (int, optional): Category ID
        - min_stock_level (int, optional): Minimum stock level
        - current_stock (int, optional): Initial stock
        - unit_price (float): Unit price
    """
    try:
        identity = get_jwt_identity()
        current_user = db.session.get(User, identity['id'])
        if not current_user:
            logger.error("User not found for identity: %s", identity)
            return jsonify({'status': 'error', 'message': 'User not found'}), 404

        if request.method == 'GET':
            category_id = request.args.get('category_id', type=int)
            store_id = request.args.get('store_id', type=int)
            low_stock = request.args.get('low_stock', type=bool, default=False)
            search = request.args.get('search', '')
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 20, type=int)

            store_ids = get_store_ids(current_user.id, current_user.role, store_id)
            if not store_ids:
                logger.warning(f"No accessible stores for user ID: {current_user.id}")
                return jsonify({
                    'status': 'success',
                    'message': 'No accessible stores for this user',
                    'products': [],
                    'total': 0,
                    'page': page,
                    'pages': 0
                }), 200

            query = db.session.query(Product).filter(Product.store_id.in_(store_ids))
            if category_id:
                query = query.filter_by(category_id=category_id)
            if low_stock:
                query = query.filter(Product.current_stock <= Product.min_stock_level)
            if search:
                query = query.filter(Product.name.ilike(f'%{search}%'))

            paginated = query.paginate(page=page, per_page=per_page, error_out=False)
            products = paginated.items
            result = ProductSchema(many=True).dump(products)

            for product, serialized in zip(products, result):
                store = db.session.get(Store, product.store_id)
                category = db.session.get(ProductCategory, product.category_id) if product.category_id else None
                serialized['store_id'] = product.store_id
                serialized['store_name'] = store.name if store else None
                serialized['category_name'] = category.name if category else None
                serialized['low_stock'] = product.current_stock <= product.min_stock_level

            logger.info("Fetched %d products for user ID: %s, role: %s, page: %d, store_ids: %s, search: %s",
                        paginated.total, current_user.id, current_user.role.name, page, store_ids, search)
            return jsonify({
                'status': 'success',
                'products': result,
                'total': paginated.total,
                'page': page,
                'pages': paginated.pages
            }), 200

        if request.method == 'POST':
            if current_user.role not in [UserRole.ADMIN, UserRole.MERCHANT]:
                logger.warning("Unauthorized product creation attempt by user ID: %s, role: %s",
                               current_user.id, current_user.role.name)
                return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403

            data = request.get_json()
            if not data:
                logger.error("No request body provided for product creation by user ID: %s", current_user.id)
                return jsonify({'status': 'error', 'message': 'Request body is required'}), 400

            schema = ProductSchema()
            errors = schema.validate(data)
            if errors:
                logger.error("Validation errors in product creation by user ID: %s: %s", current_user.id, errors)
                return jsonify({'status': 'error', 'message': 'Validation error', 'errors': errors}), 400

            store_ids = get_store_ids(current_user.id, current_user.role, data['store_id'])
            if data['store_id'] not in store_ids:
                logger.error("Store not accessible: %s for user ID: %s", data['store_id'], current_user.id)
                return jsonify({'status': 'error', 'message': 'Store not accessible'}), 403

            store = db.session.get(Store, data['store_id'])
            if not store:
                logger.error("Store not found: %s for user ID: %s", data['store_id'], current_user.id)
                return jsonify({'status': 'error', 'message': 'Store not found'}), 404

            category_id = data.get('category_id')
            if category_id:
                category = db.session.get(ProductCategory, category_id)
                if not category:
                    logger.error("Category not found: %s for user ID: %s", category_id, current_user.id)
                    return jsonify({'status': 'error', 'message': 'Category not found'}), 404

            product = Product(
                name=data['name'],
                sku=data.get('sku'),
                category_id=category_id,
                store_id=data['store_id'],
                min_stock_level=data.get('min_stock_level', 5),
                current_stock=data.get('current_stock', 0),
                unit_price=data['unit_price']
            )

            db.session.add(product)
            db.session.flush()

            # Notify about new product
            users_to_notify = db.session.query(User).filter(
                user_store.c.user_id == User.id,
                user_store.c.store_id == product.store_id,
                User.role.in_([UserRole.ADMIN, UserRole.MERCHANT])
            ).all()
            for user in users_to_notify:
                notification = Notification(
                    user_id=user.id,
                    message=f"New product '{product.name}' added to store.",
                    type=NotificationType.PRODUCT_ADDED,
                    related_entity_id=product.id,
                    related_entity_type='Product'
                )
                db.session.add(notification)
                db.session.flush()
                socketio.emit('new_notification', {
                    'id': notification.id,
                    'message': notification.message,
                    'type': notification.type.name,
                    'related_entity_id': notification.related_entity_id,
                    'related_entity_type': notification.related_entity_type,
                    'created_at': notification.created_at.isoformat()
                }, room=f'user_{user.id}')

            if product.current_stock <= product.min_stock_level:
                for user in users_to_notify:
                    notification = Notification(
                        user_id=user.id,
                        message=f"New product '{product.name}' added with low stock: {product.current_stock} units.",
                        type=NotificationType.LOW_STOCK,
                        related_entity_id=product.id,
                        related_entity_type='Product'
                    )
                    db.session.add(notification)
                    db.session.flush()
                    socketio.emit('new_notification', {
                        'id': notification.id,
                        'message': notification.message,
                        'type': notification.type.name,
                        'related_entity_id': notification.related_entity_id,
                        'related_entity_type': notification.related_entity_type,
                        'created_at': notification.created_at.isoformat()
                    }, room=f'user_{user.id}')

            db.session.commit()
            logger.info("Product created: %s (ID: %s) by user ID: %s, role: %s",
                        product.name, product.id, current_user.id, current_user.role.name)
            return jsonify({
                'status': 'success',
                'message': 'Product created',
                'product': ProductSchema().dump(product)
            }), 201

    except Exception as e:
        db.session.rollback()
        logger.error("Error in manage_products for user ID: %s: %s", identity.get('id', 'unknown'), str(e))
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@inventory_bp.route('/entries', methods=['GET', 'POST'])
@jwt_required()
def manage_entries():
    """
    GET: Get inventory entries with filters and pagination.
    POST: Create a new inventory entry and update product stock.
    Note: quantity_spoiled affects stock calculations but spoilage value for reporting is derived as (total_sales_revenue / 15).
    Query Parameters (GET):
        - product_id (int, optional): Filter by product ID
        - payment_status (str, optional): Filter by payment status
        - supplier_id (int, optional): Filter by supplier ID
        - store_id (int, optional): Filter by store ID
        - clerk_id (int, optional): Filter by clerk ID
        - page (int, optional): Page number (default 1)
        - per_page (int, optional): Items per page (default 20)
    Request Body (POST):
        - product_id (int): Product ID
        - quantity_received (int): Quantity received
        - buying_price (float): Buying price per unit
        - selling_price (float): Selling price per unit
        - quantity_spoiled (int, optional): Quantity spoiled (affects stock, not reporting)
        - payment_status (str, optional): Payment status
        - supplier_id (int, optional): Supplier ID
        - due_date (datetime, optional): Due date
        - category_id (int, optional): Category ID
    """
    try:
        identity = get_jwt_identity()
        current_user = db.session.get(User, identity['id'])
        if not current_user:
            logger.error("User not found for identity: %s", identity)
            return jsonify({'status': 'error', 'message': 'User not found'}), 404

        if request.method == 'GET':
            product_id = request.args.get('product_id', type=int)
            payment_status = request.args.get('payment_status')
            supplier_id = request.args.get('supplier_id', type=int)
            store_id = request.args.get('store_id', type=int)
            clerk_id = request.args.get('clerk_id', type=int)
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 20, type=int)

            store_ids = get_store_ids(current_user.id, current_user.role, store_id)
            if not store_ids:
                logger.warning(f"No accessible stores for user ID: {current_user.id}")
                return jsonify({
                    'status': 'success',
                    'message': 'No accessible stores for this user',
                    'entries': [],
                    'total': 0,
                    'page': page,
                    'pages': 0
                }), 200

            query = db.session.query(InventoryEntry).\
                join(Product, InventoryEntry.product_id == Product.id).\
                join(User, InventoryEntry.recorded_by == User.id).\
                join(Store, Product.store_id == Store.id).\
                filter(Product.store_id.in_(store_ids))

            if product_id:
                query = query.filter(InventoryEntry.product_id == product_id)
            if payment_status:
                try:
                    query = query.filter(InventoryEntry.payment_status == PaymentStatus[payment_status.upper()])
                except KeyError:
                    logger.error("Invalid payment status: %s for user ID: %s", payment_status, current_user.id)
                    return jsonify({'status': 'error', 'message': 'Invalid payment status'}), 400
            if supplier_id:
                query = query.filter(InventoryEntry.supplier_id == supplier_id)
            if clerk_id:
                query = query.filter(InventoryEntry.recorded_by == clerk_id)

            paginated = query.paginate(page=page, per_page=per_page, error_out=False)
            entries = paginated.items
            result = InventoryEntrySchema(many=True).dump(entries)

            for entry, serialized in zip(entries, result):
                product = db.session.get(Product, entry.product_id)
                user = db.session.get(User, entry.recorded_by)
                store = db.session.get(Store, product.store_id)
                supplier = db.session.get(Supplier, entry.supplier_id) if entry.supplier_id else None
                serialized['product_name'] = product.name if product else None
                serialized['supplier_name'] = supplier.name if supplier else None
                serialized['clerk_id'] = entry.recorded_by
                serialized['clerk_name'] = user.name if user else None
                serialized['store_id'] = store.id if store else None
                serialized['store_name'] = store.name if store else None
                serialized['entry_date'] = entry.entry_date.isoformat()
                serialized['due_date'] = entry.due_date.isoformat() if entry.due_date else None

            logger.info("Fetched %d inventory entries for user ID: %s, role: %s, page: %d, store_ids: %s",
                        paginated.total, current_user.id, current_user.role.name, page, store_ids)
            return jsonify({
                'status': 'success',
                'entries': result,
                'total': paginated.total,
                'page': page,
                'pages': paginated.pages
            }), 200

        if request.method == 'POST':
            if current_user.role != UserRole.CLERK:
                logger.warning("Unauthorized inventory entry creation attempt by user ID: %s, role: %s",
                               current_user.id, current_user.role.name)
                return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403

            data = request.get_json()
            if not data:
                logger.error("No request body provided for inventory entry creation by user ID: %s", current_user.id)
                return jsonify({'status': 'error', 'message': 'Request body is required'}), 400

            schema = InventoryEntrySchema()
            errors = schema.validate(data)
            if errors:
                logger.error("Validation errors in inventory entry creation by user ID: %s: %s", current_user.id, errors)
                return jsonify({'status': 'error', 'message': 'Validation error', 'errors': errors}), 400

            product = db.session.get(Product, data['product_id'])
            if not product:
                logger.error("Product not found: %s for user ID: %s", data['product_id'], current_user.id)
                return jsonify({'status': 'error', 'message': 'Product not found'}), 404

            store_ids = get_store_ids(current_user.id, current_user.role, product.store_id)
            if product.store_id not in store_ids:
                logger.warning("User ID: %s attempted to add entry for unauthorized store: %s",
                               current_user.id, product.store_id)
                return jsonify({'status': 'error', 'message': 'You can only add entries for your store'}), 403

            supplier_id = data.get('supplier_id')
            if supplier_id:
                supplier = db.session.get(Supplier, supplier_id)
                if not supplier:
                    logger.error("Supplier not found: %s for user ID: %s", supplier_id, current_user.id)
                    return jsonify({'status': 'error', 'message': 'Supplier not found'}), 404

            category_id = data.get('category_id')
            if category_id:
                category = db.session.get(ProductCategory, category_id)
                if not category:
                    logger.error("Category not found: %s for user ID: %s", category_id, current_user.id)
                    return jsonify({'status': 'error', 'message': 'Category not found'}), 404

            quantity_spoiled = data.get('quantity_spoiled', 0)
            if quantity_spoiled > data['quantity_received']:
                logger.error("Quantity spoiled %s exceeds quantity received %s for user ID: %s",
                             quantity_spoiled, data['quantity_received'], current_user.id)
                return jsonify({'status': 'error', 'message': 'Quantity spoiled must be less than quantity received'}), 400

            with db.session.begin_nested():
                entry = InventoryEntry(
                    product_id=data['product_id'],
                    store_id=product.store_id,
                    category_id=category_id,
                    quantity_received=data['quantity_received'],
                    quantity_spoiled=quantity_spoiled,
                    buying_price=data['buying_price'],
                    selling_price=data['selling_price'],
                    payment_status=PaymentStatus[data.get('payment_status', 'UNPAID').upper()],
                    supplier_id=supplier_id,
                    recorded_by=current_user.id,
                    due_date=data.get('due_date')
                )

                db.session.add(entry)
                product.current_stock += (entry.quantity_received - entry.quantity_spoiled)
                db.session.flush()

                # Notify about inventory entry
                users_to_notify = db.session.query(User).filter(
                    user_store.c.user_id == User.id,
                    user_store.c.store_id == product.store_id,
                    User.role.in_([UserRole.ADMIN, UserRole.MERCHANT])
                ).all()
                for user in users_to_notify:
                    notification = Notification(
                        user_id=user.id,
                        message=f"New inventory entry for '{product.name}' recorded by {current_user.name}",
                        type=NotificationType.INVENTORY_ENTRY,
                        related_entity_id=entry.id,
                        related_entity_type='InventoryEntry'
                    )
                    db.session.add(notification)
                    db.session.flush()
                    socketio.emit('new_notification', {
                        'id': notification.id,
                        'message': notification.message,
                        'type': notification.type.name,
                        'related_entity_id': notification.related_entity_id,
                        'related_entity_type': notification.related_entity_type,
                        'created_at': notification.created_at.isoformat()
                    }, room=f'user_{user.id}')

                if quantity_spoiled > 0:
                    for user in users_to_notify:
                        notification = Notification(
                            user_id=user.id,
                            message=f"Inventory entry for '{product.name}' recorded with {quantity_spoiled} spoiled units (affects stock only; spoilage value derived from sales).",
                            type=NotificationType.SPOILAGE,
                            related_entity_id=entry.id,
                            related_entity_type='InventoryEntry'
                        )
                        db.session.add(notification)
                        db.session.flush()
                        socketio.emit('new_notification', {
                            'id': notification.id,
                            'message': notification.message,
                            'type': notification.type.name,
                            'related_entity_id': notification.related_entity_id,
                            'related_entity_type': notification.related_entity_type,
                            'created_at': notification.created_at.isoformat()
                        }, room=f'user_{user.id}')

                if product.current_stock <= product.min_stock_level:
                    for user in users_to_notify:
                        notification = Notification(
                            user_id=user.id,
                            message=f"Product '{product.name}' stock is low: {product.current_stock} units.",
                            type=NotificationType.LOW_STOCK,
                            related_entity_id=product.id,
                            related_entity_type='Product'
                        )
                        db.session.add(notification)
                        db.session.flush()
                        socketio.emit('new_notification', {
                            'id': notification.id,
                            'message': notification.message,
                            'type': notification.type.name,
                            'related_entity_id': notification.related_entity_id,
                            'related_entity_type': notification.related_entity_type,
                            'created_at': notification.created_at.isoformat()
                        }, room=f'user_{user.id}')

                # Log activity
                activity = ActivityLog(
                    user_id=current_user.id,
                    action_type='STOCK_ENTRY',
                    details=f'Added {data["quantity_received"]} units of product ID {data["product_id"]}',
                    status='success'
                )
                db.session.add(activity)

            db.session.commit()
            logger.info("Inventory entry created for product: %s (ID: %s) by user ID: %s, role: %s, quantity_spoiled: %d",
                        product.name, entry.id, current_user.id, current_user.role.name, quantity_spoiled)
            return jsonify({
                'status': 'success',
                'message': 'Inventory entry created successfully',
                'entry': InventoryEntrySchema().dump(entry)
            }), 201

    except Exception as e:
        db.session.rollback()
        logger.error("Error in manage_entries for user ID: %s: %s", identity.get('id', 'unknown'), str(e))
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@inventory_bp.route('/entries/<int:entry_id>', methods=['PUT', 'DELETE'])
@jwt_required()
def modify_entry(entry_id):
    """
    PUT: Update an existing inventory entry and adjust product stock.
    DELETE: Delete an inventory entry and adjust product stock.
    Note: quantity_spoiled affects stock calculations but spoilage value for reporting is derived as (total_sales_revenue / 15).
    Request Body (PUT):
        - quantity_received (int, optional): Updated quantity received
        - quantity_spoiled (int, optional): Updated quantity spoiled (affects stock, not reporting)
        - buying_price (float, optional): Updated buying price
        - selling_price (float, optional): Updated selling price
        - payment_status (str, optional): Updated payment status
        - supplier_id (int, optional): Updated supplier ID
        - due_date (datetime, optional): Updated due date
        - category_id (int, optional): Updated category ID
    """
    try:
        identity = get_jwt_identity()
        current_user = db.session.get(User, identity['id'])
        if not current_user:
            logger.error("User not found for identity: %s", identity)
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        if current_user.role == UserRole.CLERK:
            logger.warning("Unauthorized modify entry attempt by clerk ID: %s", current_user.id)
            return jsonify({'status': 'error', 'message': 'Unauthorized to modify inventory entries'}), 403

        entry = db.session.get(InventoryEntry, entry_id)
        if not entry:
            logger.error("Inventory entry not found: %s for user ID: %s", entry_id, current_user.id)
            return jsonify({'status': 'error', 'message': 'Inventory entry not found'}), 404

        product = db.session.get(Product, entry.product_id)
        if not product:
            logger.error("Product not found for entry: %s for user ID: %s", entry_id, current_user.id)
            return jsonify({'status': 'error', 'message': 'Product not found'}), 404

        store_ids = get_store_ids(current_user.id, current_user.role, product.store_id)
        if product.store_id not in store_ids:
            logger.warning("User ID: %s attempted to modify entry for unauthorized store: %s",
                           current_user.id, product.store_id)
            return jsonify({'status': 'error', 'message': 'You can only modify entries for your store'}), 403

        if request.method == 'PUT':
            data = request.get_json()
            if not data:
                logger.error("No data provided for updating entry: %s by user ID: %s", entry_id, current_user.id)
                return jsonify({'status': 'error', 'message': 'No data provided for update'}), 400

            schema = InventoryEntrySchema(partial=True)
            errors = schema.validate(data)
            if errors:
                logger.error("Validation errors in updating entry %s by user ID: %s: %s", entry_id, current_user.id, errors)
                return jsonify({'status': 'error', 'message': 'Validation error', 'errors': errors}), 400

            with db.session.begin_nested():
                previous_net_quantity = entry.quantity_received - entry.quantity_spoiled
                product.current_stock -= previous_net_quantity

                if 'quantity_received' in data:
                    entry.quantity_received = data['quantity_received']
                quantity_spoiled = data.get('quantity_spoiled', entry.quantity_spoiled)
                if 'quantity_spoiled' in data:
                    quantity_spoiled = data['quantity_spoiled']
                if quantity_spoiled > entry.quantity_received:
                    logger.error("Quantity spoiled %s exceeds quantity received %s for entry: %s by user ID: %s",
                                 quantity_spoiled, entry.quantity_received, entry_id, current_user.id)
                    return jsonify({'status': 'error', 'message': 'Quantity spoiled must be less than quantity received'}), 400
                entry.quantity_spoiled = quantity_spoiled
                if 'buying_price' in data:
                    entry.buying_price = data['buying_price']
                if 'selling_price' in data:
                    entry.selling_price = data['selling_price']
                if 'payment_status' in data:
                    try:
                        entry.payment_status = PaymentStatus[data['payment_status'].upper()]
                    except KeyError:
                        logger.error("Invalid payment status: %s for entry: %s by user ID: %s",
                                     data['payment_status'], entry_id, current_user.id)
                        return jsonify({'status': 'error', 'message': 'Invalid payment status'}), 400
                if 'supplier_id' in data:
                    supplier_id = data['supplier_id']
                    if supplier_id:
                        supplier = db.session.get(Supplier, supplier_id)
                        if not supplier:
                            logger.error("Supplier not found: %s for entry: %s by user ID: %s",
                                         supplier_id, entry_id, current_user.id)
                            return jsonify({'status': 'error', 'message': 'Supplier not found'}), 404
                    entry.supplier_id = supplier_id
                if 'due_date' in data:
                    entry.due_date = data['due_date']
                if 'category_id' in data:
                    category_id = data['category_id']
                    if category_id:
                        category = db.session.get(ProductCategory, category_id)
                        if not category:
                            logger.error("Category not found: %s for entry: %s by user ID: %s",
                                         category_id, entry_id, current_user.id)
                            return jsonify({'status': 'error', 'message': 'Category not found'}), 404
                    entry.category_id = category_id

                new_net_quantity = entry.quantity_received - entry.quantity_spoiled
                product.current_stock += new_net_quantity
                db.session.flush()

                # Notify about stock update
                users_to_notify = db.session.query(User).filter(
                    user_store.c.user_id == User.id,
                    user_store.c.store_id == product.store_id,
                    User.role.in_([UserRole.ADMIN, UserRole.MERCHANT])
                ).all()
                for user in users_to_notify:
                    notification = Notification(
                        user_id=user.id,
                        message=f"Inventory entry for '{product.name}' updated with {entry.quantity_received} units.",
                        type=NotificationType.STOCK_UPDATED,
                        related_entity_id=entry.id,
                        related_entity_type='InventoryEntry'
                    )
                    db.session.add(notification)
                    db.session.flush()
                    socketio.emit('new_notification', {
                        'id': notification.id,
                        'message': notification.message,
                        'type': notification.type.name,
                        'related_entity_id': notification.related_entity_id,
                        'related_entity_type': notification.related_entity_type,
                        'created_at': notification.created_at.isoformat()
                    }, room=f'user_{user.id}')

                if quantity_spoiled > 0:
                    for user in users_to_notify:
                        notification = Notification(
                            user_id=user.id,
                            message=f"Inventory entry for '{product.name}' updated with {quantity_spoiled} spoiled units (affects stock only; spoilage value derived from sales).",
                            type=NotificationType.SPOILAGE,
                            related_entity_id=entry.id,
                            related_entity_type='InventoryEntry'
                        )
                        db.session.add(notification)
                        db.session.flush()
                        socketio.emit('new_notification', {
                            'id': notification.id,
                            'message': notification.message,
                            'type': notification.type.name,
                            'related_entity_id': notification.related_entity_id,
                            'related_entity_type': notification.related_entity_type,
                            'created_at': notification.created_at.isoformat()
                        }, room=f'user_{user.id}')

                if product.current_stock <= product.min_stock_level:
                    for user in users_to_notify:
                        notification = Notification(
                            user_id=user.id,
                            message=f"Product '{product.name}' stock updated to low level: {product.current_stock} units.",
                            type=NotificationType.LOW_STOCK,
                            related_entity_id=product.id,
                            related_entity_type='Product'
                        )
                        db.session.add(notification)
                        db.session.flush()
                        socketio.emit('new_notification', {
                            'id': notification.id,
                            'message': notification.message,
                            'type': notification.type.name,
                            'related_entity_id': notification.related_entity_id,
                            'related_entity_type': notification.related_entity_type,
                            'created_at': notification.created_at.isoformat()
                        }, room=f'user_{user.id}')

                # Log activity
                activity = ActivityLog(
                    user_id=current_user.id,
                    action_type='UPDATE_STOCK_ENTRY',
                    details=f'Updated entry {entry_id} for product ID {entry.product_id}',
                    status='success'
                )
                db.session.add(activity)

            db.session.commit()
            logger.info("Inventory entry updated: %s by user ID: %s, role: %s, quantity_spoiled: %d",
                        entry_id, current_user.id, current_user.role.name, entry.quantity_spoiled)
            return jsonify({
                'status': 'success',
                'message': 'Inventory entry updated successfully',
                'inventory_entry': InventoryEntrySchema().dump(entry)
            }), 200

        if request.method == 'DELETE':
            with db.session.begin_nested():
                net_quantity = entry.quantity_received - entry.quantity_spoiled
                product.current_stock -= net_quantity
                db.session.delete(entry)
                db.session.flush()

                if product.current_stock <= product.min_stock_level:
                    users_to_notify = db.session.query(User).filter(
                        user_store.c.user_id == User.id,
                        user_store.c.store_id == product.store_id,
                        User.role.in_([UserRole.ADMIN, UserRole.MERCHANT])
                    ).all()
                    for user in users_to_notify:
                        notification = Notification(
                            user_id=user.id,
                            message=f"Product '{product.name}' stock updated to low level: {product.current_stock} units after entry deletion.",
                            type=NotificationType.LOW_STOCK,
                            related_entity_id=product.id,
                            related_entity_type='Product'
                        )
                        db.session.add(notification)
                        db.session.flush()
                        socketio.emit('new_notification', {
                            'id': notification.id,
                            'message': notification.message,
                            'type': notification.type.name,
                            'related_entity_id': notification.related_entity_id,
                            'related_entity_type': notification.related_entity_type,
                            'created_at': notification.created_at.isoformat()
                        }, room=f'user_{user.id}')

                # Log activity
                activity = ActivityLog(
                    user_id=current_user.id,
                    action_type='DELETE_STOCK_ENTRY',
                    details=f'Deleted entry {entry_id} for product ID {entry.product_id}',
                    status='success'
                )
                db.session.add(activity)

            db.session.commit()
            logger.info("Inventory entry deleted: %s by user ID: %s, role: %s", entry_id, current_user.id, current_user.role.name)
            return jsonify({
                'status': 'success',
                'message': 'Inventory entry deleted successfully'
            }), 200

    except Exception as e:
        db.session.rollback()
        logger.error("Error in modify_entry for user ID: %s: %s", identity.get('id', 'unknown'), str(e))
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@inventory_bp.route('/supply-requests', methods=['GET', 'POST'])
@jwt_required()
def manage_supply_requests():
    """
    GET: Get supply requests with filters and pagination.
    POST: Create a new supply request and emit WebSocket event.
    Query Parameters (GET):
        - product_id (int, optional): Filter by product ID
        - status (str, optional): Filter by request status
        - clerk_id (int, optional): Filter by clerk ID
        - store_id (int, optional): Filter by store ID
        - page (int, optional): Page number (default 1)
        - per_page (int, optional): Items per page (default 20)
    Request Body (POST):
        - product_id (int): Product ID
        - quantity_requested (int): Quantity requested
    """
    try:
        identity = get_jwt_identity()
        current_user = db.session.get(User, identity['id'])
        if not current_user:
            logger.error("User not found for identity: %s", identity)
            return jsonify({'status': 'error', 'message': 'User not found'}), 404

        if request.method == 'GET':
            product_id = request.args.get('product_id', type=int)
            status = request.args.get('status')
            clerk_id = request.args.get('clerk_id', type=int)
            store_id = request.args.get('store_id', type=int)
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 20, type=int)

            store_ids = get_store_ids(current_user.id, current_user.role, store_id)
            if not store_ids:
                logger.warning(f"No accessible stores for user ID: {current_user.id}")
                return jsonify({
                    'status': 'success',
                    'message': 'No accessible stores for this user',
                    'requests': [],
                    'total': 0,
                    'page': page,
                    'pages': 0
                }), 200

            query = db.session.query(SupplyRequest).\
                join(Product, SupplyRequest.product_id == Product.id).\
                filter(Product.store_id.in_(store_ids))

            if product_id:
                query = query.filter(SupplyRequest.product_id == product_id)
            if status:
                try:
                    query = query.filter(SupplyRequest.status == RequestStatus[status.upper()])
                except KeyError:
                    logger.error("Invalid request status: %s for user ID: %s", status, current_user.id)
                    return jsonify({'status': 'error', 'message': 'Invalid request status'}), 400
            if clerk_id:
                query = query.filter(SupplyRequest.clerk_id == clerk_id)
            if current_user.role == UserRole.CLERK:
                query = query.filter(SupplyRequest.clerk_id == current_user.id)

            paginated = query.paginate(page=page, per_page=per_page, error_out=False)
            requests = paginated.items
            result = SupplyRequestSchema(many=True).dump(requests)

            for req, serialized in zip(requests, result):
                product = db.session.get(Product, req.product_id)
                clerk = db.session.get(User, req.clerk_id)
                admin = db.session.get(User, req.admin_id) if req.admin_id else None
                store = db.session.get(Store, req.store_id) if req.store_id else None
                serialized['product_name'] = product.name if product else None
                serialized['clerk_id'] = req.clerk_id
                serialized['clerk_name'] = clerk.name if clerk else None
                serialized['admin_name'] = admin.name if admin else None
                serialized['store_id'] = store.id if store else None
                serialized['store_name'] = store.name if store else None
                serialized['current_stock'] = product.current_stock if product else 0

            logger.info("Fetched %d supply requests for user ID: %s, role: %s, page: %d, store_ids: %s",
                        paginated.total, current_user.id, current_user.role.name, page, store_ids)
            return jsonify({
                'status': 'success',
                'requests': result,
                'total': paginated.total,
                'page': page,
                'pages': paginated.pages
            }), 200

        if request.method == 'POST':
            if current_user.role != UserRole.CLERK:
                logger.warning("Unauthorized supply request creation attempt by user ID: %s, role: %s",
                               current_user.id, current_user.role.name)
                return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403

            data = request.get_json()
            if not data:
                logger.error("No request body provided for supply request creation by user ID: %s", current_user.id)
                return jsonify({'status': 'error', 'message': 'Request body is required'}), 400

            schema = SupplyRequestSchema()
            errors = schema.validate(data)
            if errors:
                logger.error("Validation errors in supply request creation by user ID: %s: %s", current_user.id, errors)
                return jsonify({'status': 'error', 'message': 'Validation error', 'errors': errors}), 400

            product = db.session.get(Product, data['product_id'])
            if not product:
                logger.error("Product not found: %s for user ID: %s", data['product_id'], current_user.id)
                return jsonify({'status': 'error', 'message': 'Product not found'}), 404

            store_ids = get_store_ids(current_user.id, current_user.role, product.store_id)
            if product.store_id not in store_ids:
                logger.warning("User ID: %s attempted to request supply for unauthorized store: %s",
                               current_user.id, product.store_id)
                return jsonify({'status': 'error', 'message': 'You can only request supplies for your store'}), 403

            quantity_requested = data.get('quantity_requested', product.min_stock_level * 2)

            with db.session.begin_nested():
                supply_request = SupplyRequest(
                    product_id=product.id,
                    quantity_requested=quantity_requested,
                    clerk_id=current_user.id,
                    store_id=product.store_id,
                    status=RequestStatus.PENDING
                )

                db.session.add(supply_request)
                db.session.flush()

                admins = db.session.query(User).filter(
                    user_store.c.user_id == User.id,
                    user_store.c.store_id == product.store_id,
                    User.role == UserRole.ADMIN
                ).all()
                for admin in admins:
                    notification = Notification(
                        user_id=admin.id,
                        message=f"New supply request for {product.name} from {current_user.name}.",
                        type=NotificationType.SUPPLY_REQUEST,
                        related_entity_id=supply_request.id,
                        related_entity_type='SupplyRequest'
                    )
                    db.session.add(notification)
                    db.session.flush()
                    socketio.emit('supply_request', {
                        'request_id': supply_request.id,
                        'product_id': product.id,
                        'product_name': product.name,
                        'quantity': quantity_requested,
                        'clerk_id': current_user.id,
                        'clerk_name': current_user.name,
                        'store_id': product.store_id,
                        'current_stock': product.current_stock,
                        'message': f"New supply request for {product.name}: {quantity_requested} units",
                        'type': 'SUPPLY_REQUEST',
                        'timestamp': datetime.utcnow().isoformat()
                    }, room=f'user_{admin.id}')

                # Log activity
                activity = ActivityLog(
                    user_id=current_user.id,
                    action_type='SUPPLY_REQUEST_CREATE',
                    details=f'Requested {quantity_requested} units of {product.name}',
                    status='success'
                )
                db.session.add(activity)

            db.session.commit()
            logger.info("Supply request created for product: %s (ID: %s) by user ID: %s, role: %s",
                        product.name, supply_request.id, current_user.id, current_user.role.name)
            return jsonify({
                'status': 'success',
                'message': 'Supply request submitted successfully',
                'request': SupplyRequestSchema().dump(supply_request)
            }), 201

    except Exception as e:
        db.session.rollback()
        logger.error("Error in manage_supply_requests for user ID: %s: %s", identity.get('id', 'unknown'), str(e))
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@inventory_bp.route('/supply-requests/<int:request_id>/approve', methods=['PUT'])
@jwt_required()
def approve_supply_request(request_id):
    """
    Approve a supply request (admin only).
    """
    try:
        identity = get_jwt_identity()
        current_user = db.session.get(User, identity['id'])
        if not current_user or current_user.role != UserRole.ADMIN:
            logger.warning("Unauthorized supply request approval attempt by user ID: %s, role: %s",
                           identity.get('id', 'unknown'), current_user.role.name if current_user else 'none')
            return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403

        request_obj = db.session.get(SupplyRequest, request_id)
        if not request_obj:
            logger.error("Supply request not found: %s for user ID: %s", request_id, current_user.id)
            return jsonify({'status': 'error', 'message': 'Request not found'}), 404

        product = db.session.get(Product, request_obj.product_id)
        if not product:
            logger.error("Product not found for supply request: %s for user ID: %s", request_id, current_user.id)
            return jsonify({'status': 'error', 'message': 'Product not found'}), 404

        store_ids = get_store_ids(current_user.id, current_user.role, request_obj.store_id)
        if request_obj.store_id not in store_ids:
            logger.warning("User ID: %s attempted to approve supply request for unauthorized store: %s",
                           current_user.id, request_obj.store_id)
            return jsonify({'status': 'error', 'message': 'Unauthorized store access'}), 403

        if request_obj.status != RequestStatus.PENDING:
            logger.error("Attempt to approve non-pending supply request: %s, current status: %s by user ID: %s",
                         request_id, request_obj.status.name, current_user.id)
            return jsonify({'status': 'error', 'message': 'Request already processed'}), 400

        with db.session.begin_nested():
            request_obj.status = RequestStatus.APPROVED
            request_obj.admin_id = current_user.id
            request_obj.approval_date = datetime.utcnow()
            
            clerk = db.session.get(User, request_obj.clerk_id)
            
            # Notify the clerk
            notification = Notification(
                user_id=clerk.id,
                message=f"Your supply request for {product.name} has been approved",
                type=NotificationType.SUPPLY_REQUEST,
                related_entity_id=request_obj.id,
                related_entity_type='SupplyRequest'
            )
            db.session.add(notification)
            db.session.flush()
            
            # Send real-time update to clerk
            socketio.emit('supply_request_status', {
                'request_id': request_obj.id,
                'status': 'approved',
                'product_name': product.name,
                'admin_name': current_user.name,
                'timestamp': datetime.utcnow().isoformat()
            }, room=f'user_{clerk.id}')

            # Log activity
            activity = ActivityLog(
                user_id=current_user.id,
                action_type='SUPPLY_REQUEST_APPROVE',
                details=f'Approved request for {product.name}',
                status='success'
            )
            db.session.add(activity)

        db.session.commit()
        logger.info("Supply request %s approved by user ID: %s, role: %s",
                    request_id, current_user.id, current_user.role.name)
        return jsonify({
            'status': 'success',
            'message': 'Request approved',
            'request': SupplyRequestSchema().dump(request_obj)
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error("Error in approve_supply_request for user ID: %s: %s", identity.get('id', 'unknown'), str(e))
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@inventory_bp.route('/supply-requests/<int:request_id>/decline', methods=['PUT'])
@jwt_required()
def decline_supply_request(request_id):
    """
    Decline a supply request (admin only).
    Request Body:
        - decline_reason (str): Reason for declining
    """
    try:
        identity = get_jwt_identity()
        current_user = db.session.get(User, identity['id'])
        if not current_user or current_user.role != UserRole.ADMIN:
            logger.warning("Unauthorized supply request decline attempt by user ID: %s, role: %s",
                           identity.get('id', 'unknown'), current_user.role.name if current_user else 'none')
            return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403

        request_obj = db.session.get(SupplyRequest, request_id)
        if not request_obj:
            logger.error("Supply request not found: %s for user ID: %s", request_id, current_user.id)
            return jsonify({'status': 'error', 'message': 'Request not found'}), 404

        product = db.session.get(Product, request_obj.product_id)
        if not product:
            logger.error("Product not found for supply request: %s for user ID: %s", request_id, current_user.id)
            return jsonify({'status': 'error', 'message': 'Product not found'}), 404

        store_ids = get_store_ids(current_user.id, current_user.role, request_obj.store_id)
        if request_obj.store_id not in store_ids:
            logger.warning("User ID: %s attempted to decline supply request for unauthorized store: %s",
                           current_user.id, request_obj.store_id)
            return jsonify({'status': 'error', 'message': 'Unauthorized store access'}), 403

        data = request.get_json()
        if not data or not data.get('decline_reason'):
            logger.error("Decline reason missing for supply request: %s by user ID: %s", request_id, current_user.id)
            return jsonify({'status': 'error', 'message': 'Decline reason required'}), 400

        if request_obj.status != RequestStatus.PENDING:
            logger.error("Attempt to decline non-pending supply request: %s, current status: %s by user ID: %s",
                         request_id, request_obj.status.name, current_user.id)
            return jsonify({'status': 'error', 'message': 'Request already processed'}), 400

        with db.session.begin_nested():
            request_obj.status = RequestStatus.DECLINED
            request_obj.admin_id = current_user.id
            request_obj.decline_reason = data['decline_reason']
            request_obj.updated_at = datetime.utcnow()
            
            clerk = db.session.get(User, request_obj.clerk_id)
            
            # Notify the clerk
            notification = Notification(
                user_id=clerk.id,
                message=f"Your supply request for {product.name} was declined. Reason: {data['decline_reason']}",
                type=NotificationType.SUPPLY_REQUEST,
                related_entity_id=request_obj.id,
                related_entity_type='SupplyRequest'
            )
            db.session.add(notification)
            db.session.flush()
            
            # Send real-time update to clerk
            socketio.emit('supply_request_status', {
                'request_id': request_obj.id,
                'status': 'declined',
                'product_name': product.name,
                'admin_name': current_user.name,
                'decline_reason': data['decline_reason'],
                'timestamp': datetime.utcnow().isoformat()
            }, room=f'user_{clerk.id}')

            # Log activity
            activity = ActivityLog(
                user_id=current_user.id,
                action_type='SUPPLY_REQUEST_DECLINE',
                details=f'Declined request for {product.name} with reason: {data["decline_reason"]}',
                status='success'
            )
            db.session.add(activity)

        db.session.commit()
        logger.info("Supply request %s declined by user ID: %s, role: %s",
                    request_id, current_user.id, current_user.role.name)
        return jsonify({
            'status': 'success',
            'message': 'Request declined',
            'request': SupplyRequestSchema().dump(request_obj)
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error("Error in decline_supply_request for user ID: %s: %s", identity.get('id', 'unknown'), str(e))
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@inventory_bp.route('/update-payment', methods=['PUT'])
@jwt_required()
def update_payment():
    """
    Update the payment status of one or more inventory entries to PAID.
    Request Body:
        - entry_ids (list of int): List of inventory entry IDs to update
    """
    try:
        identity = get_jwt_identity()
        current_user = db.session.get(User, identity['id'])
        if not current_user or current_user.role not in [UserRole.MERCHANT, UserRole.ADMIN]:
            logger.warning("Unauthorized payment update attempt by user ID: %s, role: %s",
                           identity.get('id', 'unknown'), current_user.role.name if current_user else 'none')
            return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403

        data = request.get_json()
        if not data or not data.get('entry_ids'):
            logger.error("No entry IDs provided for payment update by user ID: %s", current_user.id)
            return jsonify({'status': 'error', 'message': 'Entry IDs are required'}), 400

        entry_ids = data['entry_ids']
        updated_entries = []

        with db.session.begin_nested():
            for entry_id in entry_ids:
                entry = db.session.get(InventoryEntry, entry_id)
                if not entry:
                    logger.warning("Inventory entry not found: %s for user ID: %s", entry_id, current_user.id)
                    continue

                product = db.session.get(Product, entry.product_id)
                if not product:
                    logger.warning("Product not found for entry: %s for user ID: %s", entry_id, current_user.id)
                    continue

                store_ids = get_store_ids(current_user.id, current_user.role, product.store_id)
                if product.store_id not in store_ids:
                    logger.warning("User ID: %s attempted to update payment for unauthorized store: %s",
                                   current_user.id, product.store_id)
                    continue

                entry.payment_status = PaymentStatus.PAID
                entry.payment_date = datetime.utcnow()
                updated_entries.append(entry)

                users_to_notify = db.session.query(User).filter(
                    user_store.c.user_id == User.id,
                    user_store.c.store_id == product.store_id,
                    User.role.in_([UserRole.ADMIN, UserRole.MERCHANT])
                ).all()
                for user in users_to_notify:
                    notification = Notification(
                        user_id=user.id,
                        message=f"Payment status for inventory entry of product '{product.name}' updated to PAID.",
                        type=NotificationType.PAYMENT,
                        related_entity_id=entry.id,
                        related_entity_type='InventoryEntry'
                    )
                    db.session.add(notification)
                    db.session.flush()
                    socketio.emit('new_notification', {
                        'id': notification.id,
                        'message': notification.message,
                        'type': notification.type.name,
                        'related_entity_id': notification.related_entity_id,
                        'related_entity_type': notification.related_entity_type,
                        'created_at': notification.created_at.isoformat()
                    }, room=f'user_{user.id}')

                # Log activity
                activity = ActivityLog(
                    user_id=current_user.id,
                    action_type='PAYMENT_UPDATE',
                    details=f'Updated payment status to PAID for entry {entry_id}',
                    status='success'
                )
                db.session.add(activity)

        db.session.commit()
        logger.info("Payment updated for %d inventory entries by user ID: %s, role: %s",
                    len(updated_entries), current_user.id, current_user.role.name)
        return jsonify({
            'status': 'success',
            'message': f'Payment updated for {len(updated_entries)} entries',
            'inventory_entries': InventoryEntrySchema(many=True).dump(updated_entries)
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error("Error in update_payment for user ID: %s: %s", identity.get('id', 'unknown'), str(e))
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@inventory_bp.route('/low-stock', methods=['GET'])
@jwt_required()
def low_stock():
    """
    Get products with low stock levels for clerk alerts.
    Query Parameters:
        - store_id (int, optional): Filter by store ID
    """
    try:
        identity = get_jwt_identity()
        current_user = db.session.get(User, identity['id'])
        if not current_user:
            logger.error("User not found for identity: %s", identity)
            return jsonify({'status': 'error', 'message': 'User not found'}), 404

        store_id = request.args.get('store_id', type=int)
        store_ids = get_store_ids(current_user.id, current_user.role, store_id)
        if not store_ids:
            logger.warning(f"No accessible stores for user ID: {current_user.id}")
            return jsonify({
                'status': 'success',
                'alerts': [],
                'count': 0
            }), 200

        products = db.session.query(Product).filter(
            Product.current_stock <= Product.min_stock_level,
            Product.store_id.in_(store_ids)
        ).all()

        alerts = [{
            'product_id': p.id,
            'product_name': p.name,
            'current_stock': p.current_stock,
            'min_stock_level': p.min_stock_level,
            'store_id': p.store_id
        } for p in products]

        logger.info("Fetched %d low stock products for user ID: %s, role: %s, store_ids: %s",
                    len(alerts), current_user.id, current_user.role.name, store_ids)
        return jsonify({
            'status': 'success',
            'alerts': alerts,
            'count': len(alerts)
        }), 200

    except Exception as e:
        logger.error("Error in low_stock for user ID: %s: %s", identity.get('id', 'unknown'), str(e))
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@inventory_bp.route('/non-low-stock', methods=['GET'])
@jwt_required()
def non_low_stock():
    """
    Get products with non-low stock levels.
    Query Parameters:
        - store_id (int, optional): Filter by store ID
    """
    try:
        identity = get_jwt_identity()
        current_user = db.session.get(User, identity['id'])
        if not current_user:
            logger.error("User not found for identity: %s", identity)
            return jsonify({'status': 'error', 'message': 'User not found'}), 404

        store_id = request.args.get('store_id', type=int)
        store_ids = get_store_ids(current_user.id, current_user.role, store_id)
        if not store_ids:
            logger.warning(f"No accessible stores for user ID: {current_user.id}")
            return jsonify({
                'status': 'success',
                'message': 'No accessible stores for this user',
                'items': [],
                'count': 0
            }), 200

        query = db.session.query(Product).filter(
            Product.current_stock > Product.min_stock_level,
            Product.store_id.in_(store_ids)
        )

        products = query.all()
        result = ProductSchema(many=True).dump(products)
        for product, serialized in zip(products, result):
            store = db.session.get(Store, product.store_id)
            category = db.session.get(ProductCategory, product.category_id) if product.category_id else None
            serialized['id'] = product.id
            serialized['name'] = product.name
            serialized['store_id'] = product.store_id
            serialized['store_name'] = store.name if store else None
            serialized['category_name'] = category.name if category else None
            serialized['low_stock'] = False

        logger.info("Fetched %d non-low stock products for user ID: %s, role: %s, store_ids: %s",
                    len(result), current_user.id, current_user.role.name, store_ids)
        return jsonify({
            'status': 'success',
            'items': result,
            'count': len(result)
        }), 200

    except Exception as e:
        logger.error("Error in non_low_stock for user ID: %s: %s", identity.get('id', 'unknown'), str(e))
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@inventory_bp.route('/suppliers/<status>', methods=['GET'])
@jwt_required()
def get_suppliers(status):
    """
    Get supplier details by payment status (paid or unpaid).
    Query Parameters:
        - period (str): weekly, monthly (default: weekly)
        - store_id (int, optional): Filter by store ID
        - search (str, optional): Filter by supplier or product name
    """
    try:
        identity = get_jwt_identity()
        current_user = db.session.get(User, identity['id'])
        if not current_user:
            logger.error("User not found for identity: %s", identity)
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        if current_user.role not in [UserRole.MERCHANT, UserRole.ADMIN]:
            logger.warning("Unauthorized supplier access attempt by user ID: %s, role: %s",
                           current_user.id, current_user.role.name)
            return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403

        if status not in ['paid', 'unpaid']:
            logger.error("Invalid status: %s for user ID: %s", status, current_user.id)
            return jsonify({'status': 'error', 'message': 'Invalid status'}), 400

        period = request.args.get('period', 'weekly')
        store_id = request.args.get('store_id', type=int)
        search = request.args.get('search', '')
        start_date, end_date = get_period_dates(period)

        store_ids = get_store_ids(current_user.id, current_user.role, store_id)
        if not store_ids:
            logger.warning(f"No accessible stores for user ID: {current_user.id}")
            return jsonify({
                'status': 'success',
                'message': 'No accessible stores for this user',
                'suppliers': [],
                'total_amount': 0.0,
                'count': 0
            }), 200

        payment_status = PaymentStatus.PAID if status == 'paid' else PaymentStatus.UNPAID
        query = db.session.query(InventoryEntry).\
            join(Product, InventoryEntry.product_id == Product.id).\
            join(Supplier, InventoryEntry.supplier_id == Supplier.id).\
            filter(
                InventoryEntry.payment_status == payment_status,
                InventoryEntry.entry_date.between(start_date, end_date),
                Product.store_id.in_(store_ids)
            )

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (Supplier.name.ilike(search_term)) | (Product.name.ilike(search_term))
            )

        entries = query.all()
        suppliers_data = [
            {
                'id': entry.id,
                'supplier_id': entry.supplier_id,
                'supplier_name': entry.supplier.name,
                'product_id': entry.product_id,
                'product_name': entry.product.name,
                'store_id': entry.product.store_id,
                'store_name': entry.product.store.name,
                'amount_due': float(entry.buying_price * entry.quantity_received),
                'due_date': entry.due_date.isoformat() if entry.due_date else None,
                'entry_date': entry.entry_date.isoformat(),
                'payment_status': entry.payment_status.name
            } for entry in entries
        ]

        total_amount = sum(float(entry.buying_price * entry.quantity_received) for entry in entries)
        logger.info(
            "Fetched %d %s supplier entries for user ID: %s, role: %s, period: %s, store_ids: %s, search: %s, total_amount: %.2f",
            len(suppliers_data), status, current_user.id, current_user.role.name, period, store_ids, search, total_amount
        )
        return jsonify({
            'status': 'success',
            'suppliers': suppliers_data,
            'total_amount': float(total_amount),
            'count': len(suppliers_data)
        }), 200

    except Exception as e:
        logger.error("Error in get_suppliers (%s) for user ID: %s: %s", status, identity.get('id', 'unknown'), str(e))
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@inventory_bp.route('/suppliers', methods=['GET'])
@jwt_required()
def get_all_suppliers():
    """
    Get all suppliers with filters and pagination.
    Query Parameters:
        - store_id (int, optional): Filter by store ID
        - page (int, optional): Page number (default 1)
        - per_page (int, optional): Items per page (default 20)
    """
    try:
        identity = get_jwt_identity()
        current_user = db.session.get(User, identity['id'])
        if not current_user:
            logger.error("User not found for identity: %s", identity)
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        if current_user.role == UserRole.CLERK:
            logger.warning("Unauthorized supplier view attempt by clerk ID: %s", current_user.id)
            return jsonify({'status': 'error', 'message': 'Unauthorized to view suppliers'}), 403

        store_id = request.args.get('store_id', type=int)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        store_ids = get_store_ids(current_user.id, current_user.role, store_id)
        if not store_ids:
            logger.warning(f"No accessible stores for user ID: {current_user.id}")
            return jsonify({
                'status': 'success',
                'message': 'No accessible stores for this user',
                'suppliers': [],
                'total': 0,
                'page': page,
                'pages': 0
            }), 200

        query = db.session.query(Supplier).\
            join(InventoryEntry, Supplier.id == InventoryEntry.supplier_id).\
            join(Product, InventoryEntry.product_id == Product.id).\
            filter(Product.store_id.in_(store_ids)).\
            distinct(Supplier.id)

        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        logger.info("Fetched %d suppliers for user ID: %s, role: %s, page: %d, store_ids: %s",
                    paginated.total, current_user.id, current_user.role.name, page, store_ids)
        return jsonify({
            'status': 'success',
            'suppliers': SupplierSchema(many=True).dump(paginated.items),
            'total': paginated.total,
            'page': page,
            'pages': paginated.pages
        }), 200

    except Exception as e:
        logger.error("Error in get_all_suppliers for user ID: %s: %s", identity.get('id', 'unknown'), str(e))
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@inventory_bp.route('/products/search', methods=['GET'])
@jwt_required()
def search_products():
    """
    Search products by name or category.
    Query Parameters:
        - q (str): Search term
    """
    try:
        identity = get_jwt_identity()
        current_user = db.session.get(User, identity['id'])
        if not current_user:
            logger.error("User not found for identity: %s", identity)
            return jsonify({'status': 'error', 'message': 'User not found'}), 404

        search_term = request.args.get('q', '').strip()
        if not search_term:
            logger.error("Search term missing for product search by user ID: %s", current_user.id)
            return jsonify({'status': 'error', 'message': 'Search term required'}), 400

        store_ids = get_store_ids(current_user.id, current_user.role)
        if not store_ids:
            logger.warning(f"No accessible stores for user ID: {current_user.id}")
            return jsonify({
                'status': 'success',
                'message': 'No accessible stores for this user',
                'products': [],
                'count': 0
            }), 200

        query = db.session.query(Product).\
            join(ProductCategory, isouter=True).\
            filter(
                db.or_(
                    Product.name.ilike(f'%{search_term}%'),
                    ProductCategory.name.ilike(f'%{search_term}%')
                ),
                Product.store_id.in_(store_ids)
            )

        products = query.limit(50).all()
        result = ProductSchema(many=True).dump(products)

        for product, serialized in zip(products, result):
            store = db.session.get(Store, product.store_id)
            category = db.session.get(ProductCategory, product.category_id) if product.category_id else None
            serialized['store_id'] = product.store_id
            serialized['store_name'] = store.name if store else None
            serialized['category_name'] = category.name if category else None
            serialized['low_stock'] = product.current_stock <= product.min_stock_level

        logger.info("Fetched %d products for search term '%s' by user ID: %s, role: %s, store_ids: %s",
                    len(result), search_term, current_user.id, current_user.role.name, store_ids)
        return jsonify({
            'status': 'success',
            'products': result,
            'count': len(result)
        }), 200

    except Exception as e:
        logger.error("Error in search_products for user ID: %s: %s", identity.get('id', 'unknown'), str(e))
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@inventory_bp.route('/activity-logs', methods=['GET'])
@jwt_required()
def get_activity_logs():
    """
    Get activity logs for the current user.
    """
    try:
        identity = get_jwt_identity()
        current_user = db.session.get(User, identity['id'])
        if not current_user:
            logger.error("User not found for identity: %s", identity)
            return jsonify({'status': 'error', 'message': 'User not found'}), 404

        logs = ActivityLog.query.filter_by(user_id=current_user.id).order_by(ActivityLog.created_at.desc()).all()
        result = [{
            'id': log.id,
            'action_type': log.action_type,
            'details': log.details,
            'status': log.status,
            'created_at': log.created_at.isoformat()
        } for log in logs]

        logger.info("Fetched %d activity logs for user ID: %s", len(result), current_user.id)
        return jsonify({'status': 'success', 'logs': result}), 200

    except Exception as e:
        logger.error("Error in get_activity_logs for user ID: %s: %s", identity.get('id', 'unknown'), str(e))
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500