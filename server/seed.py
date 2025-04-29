# seed.py
import os
import sys
from datetime import datetime, timedelta
import random
from werkzeug.security import generate_password_hash
from flask import Flask
import uuid

# Load environment variables before importing anything that uses them
from dotenv import load_dotenv
load_dotenv()
print("DEBUG: DATABASE_URL =", os.environ.get('DATABASE_URL'))  # Debug statement

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Now import config and other modules
from extensions import db
from models import (
    User, Store, ProductCategory, Product, Supplier, 
    InventoryEntry, SupplyRequest, UserRole, UserStatus,
    PaymentStatus, RequestStatus
)
from config import config

def create_test_app(config_name='development'):
    """Create a test app for seeding with the specified configuration"""
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    # Ensure the database URI is set
    if not app.config.get('SQLALCHEMY_DATABASE_URI'):
        database_url = os.environ.get('TEST_DATABASE_URL' if config_name == 'testing' else 'DATABASE_URL')
        if not database_url:
            raise ValueError(f"{'TEST_DATABASE_URL' if config_name == 'testing' else 'DATABASE_URL'} environment variable is not set.")
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    print(f"DEBUG: App Config SQLALCHEMY_DATABASE_URI ({config_name}) =", app.config.get('SQLALCHEMY_DATABASE_URI'))  # Debug statement
    db.init_app(app)
    return app

def clear_existing_data():
    """Delete all existing data from tables without dropping them"""
    SupplyRequest.query.delete()
    InventoryEntry.query.delete()
    Product.query.delete()
    Supplier.query.delete()
    ProductCategory.query.delete()
    User.query.delete()
    Store.query.delete()
    db.session.commit()

def seed_database():
    """Seed the database with initial data"""
    # Create a merchant
    merchant = User(
        name='Test Merchant',
        email='merchant@myduka.com',
        role=UserRole.MERCHANT,
        status=UserStatus.ACTIVE
    )
    merchant.password = 'password123'  # Use the password setter
    db.session.add(merchant)
    
    # Create stores
    stores = [
        Store(name='Main Store', address='123 Main St'),
        Store(name='Downtown Branch', address='456 Park Ave'),
        Store(name='Mall Outlet', address='789 Shopping Center')
    ]
    for store in stores:
        db.session.add(store)
    
    db.session.commit()
    
    # Create admin for each store
    admins = []
    for i, store in enumerate(stores):
        admin = User(
            name=f'Admin {i+1}',
            email=f'admin{i+1}@myduka.com',
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            store_id=store.id
        )
        admin.password = 'password123'  # Use the password setter
        admins.append(admin)
        db.session.add(admin)
    
    # Create clerks for each store
    clerks = []
    for i, store in enumerate(stores):
        for j in range(2):  # 2 clerks per store
            clerk = User(
                name=f'Clerk {i+1}-{j+1}',
                email=f'clerk{i+1}{j+1}@myduka.com',
                role=UserRole.CLERK,
                status=UserStatus.ACTIVE,
                store_id=store.id
            )
            clerk.password = 'password123'  # Use the password setter
            clerks.append(clerk)
            db.session.add(clerk)
    
    db.session.commit()
    
    # Create product categories
    categories = [
        ProductCategory(name='Groceries', description='Food and household items'),
        ProductCategory(name='Electronics', description='Electronic devices'),
        ProductCategory(name='Clothing', description='Apparel and accessories'),
        ProductCategory(name='Home Goods', description='Items for the home')
    ]
    for category in categories:
        db.session.add(category)
    
    db.session.commit()
    
    # Fetch the actual category IDs
    groceries = ProductCategory.query.filter_by(name='Groceries').first()
    electronics = ProductCategory.query.filter_by(name='Electronics').first()
    clothing = ProductCategory.query.filter_by(name='Clothing').first()
    home_goods = ProductCategory.query.filter_by(name='Home Goods').first()
    
    # Create suppliers
    suppliers = [
        Supplier(name='Fresh Foods Inc.', email='john@freshfoods.com', phone='123-456-7890', address='123 Supplier St'),
        Supplier(name='Tech Supplies Ltd.', email='mary@techsupplies.com', phone='098-765-4321', address='456 Supplier Ave'),
        Supplier(name='Fashion Forward', email='bob@fashionforward.com', phone='111-222-3333', address='789 Supplier Rd'),
        Supplier(name='Home Essentials', email='alice@homeessentials.com', phone='444-555-6666', address='101 Supplier Blvd')
    ]
    for supplier in suppliers:
        db.session.add(supplier)
    
    db.session.commit()
    
    # Create products using actual category IDs
    products_data = [
        # Groceries
        {'name': 'Rice', 'category_id': groceries.id, 'min_stock_level': 10},
        {'name': 'Sugar', 'category_id': groceries.id, 'min_stock_level': 15},
        {'name': 'Flour', 'category_id': groceries.id, 'min_stock_level': 10},
        {'name': 'Cooking Oil', 'category_id': groceries.id, 'min_stock_level': 8},
        # Electronics
        {'name': 'Headphones', 'category_id': electronics.id, 'min_stock_level': 5},
        {'name': 'USB Cables', 'category_id': electronics.id, 'min_stock_level': 20},
        {'name': 'Power Banks', 'category_id': electronics.id, 'min_stock_level': 10},
        # Clothing
        {'name': 'T-Shirts', 'category_id': clothing.id, 'min_stock_level': 15},
        {'name': 'Jeans', 'category_id': clothing.id, 'min_stock_level': 10},
        # Home Goods
        {'name': 'Towels', 'category_id': home_goods.id, 'min_stock_level': 12},
        {'name': 'Plates', 'category_id': home_goods.id, 'min_stock_level': 15}
    ]
    
    products = []
    for store in stores:
        for product_data in products_data:
            product = Product(
                name=product_data['name'],
                sku=f"{product_data['name'].replace(' ', '-').lower()}-{str(uuid.uuid4())[:8]}",
                category_id=product_data['category_id'],
                store_id=store.id,
                min_stock_level=product_data['min_stock_level'],
                current_stock=0
            )
            products.append(product)
            db.session.add(product)
    
    db.session.commit()
    
    # Create inventory entries
    for product in products:
        for _ in range(3):
            quantity_received = random.randint(10, 50)
            quantity_spoiled = random.randint(0, 5)
            buying_price = random.uniform(5.0, 50.0)
            selling_price = buying_price * 1.3
            
            store_clerks = [c for c in clerks if c.store_id == product.store_id]
            if store_clerks:
                clerk = random.choice(store_clerks)
                supplier_id = random.choice(suppliers).id
                payment_status = random.choice([PaymentStatus.PAID, PaymentStatus.UNPAID])
                
                entry = InventoryEntry(
                    product_id=product.id,
                    quantity_received=quantity_received,
                    quantity_spoiled=quantity_spoiled,
                    buying_price=buying_price,
                    selling_price=selling_price,
                    payment_status=payment_status,
                    supplier_id=supplier_id,
                    recorded_by=clerk.id,
                    entry_date=datetime.utcnow() - timedelta(days=random.randint(1, 30))
                )
                db.session.add(entry)
                product.current_stock += (quantity_received - quantity_spoiled)
    
    db.session.commit()
    
    # Create supply requests
    for _ in range(10):
        product = random.choice(products)
        store_clerks = [c for c in clerks if c.store_id == product.store_id]
        if store_clerks:
            clerk = random.choice(store_clerks)
            status = random.choice(list(RequestStatus))
            request = SupplyRequest(
                product_id=product.id,
                quantity_requested=random.randint(5, 30),
                clerk_id=clerk.id,
                status=status,
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 15))
            )
            if status != RequestStatus.PENDING:
                store_admins = [a for a in admins if a.store_id == product.store_id]
                if store_admins:
                    admin = random.choice(store_admins)
                    request.admin_id = admin.id
                    if status == RequestStatus.DECLINED:
                        request.decline_reason = "Budget constraints"
            db.session.add(request)
    
    db.session.commit()
    print(f"Database ({app.config['SQLALCHEMY_DATABASE_URI']}) seeded successfully!")

if __name__ == '__main__':
    app = create_test_app(config_name='development')
    with app.app_context():
        clear_existing_data()
        seed_database()