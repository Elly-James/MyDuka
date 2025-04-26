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

def create_test_app():
    """Create a test app for seeding"""
    app = Flask(__name__)
    app.config.from_object(config['development'])
    # Ensure the database URI is set
    if not app.config.get('SQLALCHEMY_DATABASE_URI'):
        # Fallback to DATABASE_URL environment variable directly
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            raise ValueError("SQLALCHEMY_DATABASE_URI is not set. Check your .env file for DATABASE_URL.")
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    print("DEBUG: App Config SQLALCHEMY_DATABASE_URI =", app.config.get('SQLALCHEMY_DATABASE_URI'))  # Debug statement
    db.init_app(app)
    return app

def clear_existing_data():
    """Delete all existing data from tables without dropping them"""
    # Delete data in a specific order to avoid foreign key constraint issues
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
        password='password123',
        role=UserRole.MERCHANT,
        status=UserStatus.ACTIVE
    )
    db.session.add(merchant)
    
    # Create stores
    stores = [
        Store(name='Main Store', location='123 Main St'),
        Store(name='Downtown Branch', location='456 Park Ave'),
        Store(name='Mall Outlet', location='789 Shopping Center')
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
            password='password123',
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            store_id=store.id
        )
        admins.append(admin)
        db.session.add(admin)
    
    # Create clerks for each store
    clerks = []
    for i, store in enumerate(stores):
        for j in range(2):  # 2 clerks per store
            clerk = User(
                name=f'Clerk {i+1}-{j+1}',
                email=f'clerk{i+1}{j+1}@myduka.com',
                password='password123',
                role=UserRole.CLERK,
                status=UserStatus.ACTIVE,
                store_id=store.id
            )
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
    
    # Create suppliers
    suppliers = [
        Supplier(name='Fresh Foods Inc.', contact_person='John Smith', phone='123-456-7890', email='john@freshfoods.com'),
        Supplier(name='Tech Supplies Ltd.', contact_person='Mary Johnson', phone='098-765-4321', email='mary@techsupplies.com'),
        Supplier(name='Fashion Forward', contact_person='Bob Brown', phone='111-222-3333', email='bob@fashionforward.com'),
        Supplier(name='Home Essentials', contact_person='Alice Green', phone='444-555-6666', email='alice@homeessentials.com')
    ]
    for supplier in suppliers:
        db.session.add(supplier)
    
    db.session.commit()
    
    # Create products
    products_data = [
        # Groceries
        {'name': 'Rice', 'category_id': 1, 'min_stock_level': 10},
        {'name': 'Sugar', 'category_id': 1, 'min_stock_level': 15},
        {'name': 'Flour', 'category_id': 1, 'min_stock_level': 10},
        {'name': 'Cooking Oil', 'category_id': 1, 'min_stock_level': 8},
        # Electronics
        {'name': 'Headphones', 'category_id': 2, 'min_stock_level': 5},
        {'name': 'USB Cables', 'category_id': 2, 'min_stock_level': 20},
        {'name': 'Power Banks', 'category_id': 2, 'min_stock_level': 10},
        # Clothing
        {'name': 'T-Shirts', 'category_id': 3, 'min_stock_level': 15},
        {'name': 'Jeans', 'category_id': 3, 'min_stock_level': 10},
        # Home Goods
        {'name': 'Towels', 'category_id': 4, 'min_stock_level': 12},
        {'name': 'Plates', 'category_id': 4, 'min_stock_level': 15}
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
                current_stock=0  # Will be updated by inventory entries
            )
            products.append(product)
            db.session.add(product)
    
    db.session.commit()
    
    # Create inventory entries
    for product in products:
        # Multiple entries for each product
        for _ in range(3):
            quantity_received = random.randint(10, 50)
            quantity_spoiled = random.randint(0, 5)
            buying_price = random.uniform(5.0, 50.0)
            selling_price = buying_price * 1.3  # 30% markup
            
            # Find a clerk from the same store
            store_clerks = [c for c in clerks if c.store_id == product.store_id]
            if store_clerks:
                clerk = random.choice(store_clerks)
                
                # Find a supplier related to the product category
                supplier_id = random.choice(suppliers).id
                
                # Decide payment status
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
                
                # Update product stock
                product.current_stock += (quantity_received - quantity_spoiled)
    
    db.session.commit()
    
    # Create supply requests
    for _ in range(10):
        # Random product
        product = random.choice(products)
        
        # Find a clerk from the same store
        store_clerks = [c for c in clerks if c.store_id == product.store_id]
        if store_clerks:
            clerk = random.choice(store_clerks)
            
            # Create a supply request
            status = random.choice(list(RequestStatus))
            
            request = SupplyRequest(
                product_id=product.id,
                quantity_requested=random.randint(5, 30),
                clerk_id=clerk.id,
                status=status,
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 15))
            )
            
            if status != RequestStatus.PENDING:
                # Find an admin from the same store
                store_admins = [a for a in admins if a.store_id == product.store_id]
                if store_admins:
                    admin = random.choice(store_admins)
                    request.admin_id = admin.id
                    
                    if status == RequestStatus.DECLINED:
                        request.decline_reason = "Budget constraints"
            
            db.session.add(request)
    
    db.session.commit()
    print("Database seeded successfully!")

if __name__ == '__main__':
    app = create_test_app()
    with app.app_context():
        # Clear existing data without dropping tables
        clear_existing_data()
        # Seed database
        seed_database()