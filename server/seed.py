import os
import sys
import random
from datetime import datetime, timedelta
from flask import Flask
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
from sqlalchemy import func, text, inspect
from faker import Faker
from collections import defaultdict

load_dotenv()
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from extensions import db
from models import (
    User, Store, ProductCategory, Product, Supplier,
    InventoryEntry, SupplyRequest, SalesRecord,
    Invitation, PasswordReset, Notification, PaymentAudit, SalesGrowth,
    UserRole, UserStatus, PaymentStatus, RequestStatus,
    InvitationStatus, NotificationType
)
from config import config

def create_app(config_name='development'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    uri = app.config.get('SQLALCHEMY_DATABASE_URI') or os.getenv(
        'TEST_DATABASE_URL' if config_name == 'testing' else 'DATABASE_URL'
    )
    if not uri:
        raise RuntimeError("DATABASE_URL is not set")
    app.config['SQLALCHEMY_DATABASE_URI'] = uri
    db.init_app(app)
    return app

def clear_existing_data():
    """Delete all existing data while respecting foreign key constraints"""
    print("🧹 Clearing existing data...")
    inspector = inspect(db.engine)
    existing_tables = inspector.get_table_names()

    # Get foreign key constraints to determine deletion order
    table_dependencies = defaultdict(set)
    for table in existing_tables:
        for fk in inspector.get_foreign_keys(table):
            table_dependencies[table].add(fk['referred_table'])

    # Topologically sort tables to respect dependencies
    def topological_sort(tables, deps):
        result = []
        visited = set()
        temp = set()

        def dfs(table):
            if table in temp:
                return
            if table not in visited:
                temp.add(table)
                for dep in deps[table]:
                    if dep in tables:
                        dfs(dep)
                temp.remove(table)
                visited.add(table)
                result.append(table)

        for table in tables:
            dfs(table)
        return result

    deletion_order = topological_sort(existing_tables, table_dependencies)[::-1]  # Reverse for deletion

    with db.session.begin():
        for table_name in deletion_order:
            try:
                db.session.execute(text(f"DELETE FROM {table_name}"))
                print(f"🗑️ Cleared table: {table_name}")
            except Exception as e:
                print(f"⚠️ Could not delete from {table_name}: {e}")
                continue
        db.session.commit()
    print("✅ All existing data cleared.")

def ensure_tables_exist():
    """Ensure all tables defined in models exist in the database"""
    print("🔍 Checking table existence...")
    inspector = inspect(db.engine)
    existing_tables = inspector.get_table_names()
    required_tables = [t.name for t in db.metadata.tables.values()]

    missing_tables = [t for t in required_tables if t not in existing_tables]
    if missing_tables:
        print(f"🛠️ Creating missing tables: {missing_tables}")
        db.create_all()
    else:
        print("✅ All required tables exist.")

def seed_database():
    print("🌱 Starting database seeding...")
    
    fake = Faker()
    used_emails = set()  # Track used emails to ensure uniqueness

    def generate_unique_email(fn, ln, store_id, role, counter):
        """Generate a unique email for a user"""
        base = f"{fn.lower()}.{ln.lower()}{store_id}{role[:1].lower()}{counter}"
        email = f"{base}@myduka.com"
        while email in used_emails:
            counter += 1
            email = f"{fn.lower()}.{ln.lower()}{store_id}{role[:1].lower()}{counter}@myduka.com"
        used_emails.add(email)
        return email

    # --- Merchant ---
    merchant_email = 'alice.thompson@myduka.com'
    used_emails.add(merchant_email)
    merchant = User(
        name='Alice Thompson',
        email=merchant_email,
        role=UserRole.MERCHANT,
        status=UserStatus.ACTIVE,
        _password=generate_password_hash('password123')
    )
    db.session.add(merchant)
    db.session.commit()

    # --- Stores ---
    stores = []
    store_names = [
        'Nairobi Central', 'Mombasa Market', 'Kisumu Hub', 'Eldoret Plaza',
        'Nakuru Depot', 'Nyeri Store', 'Thika Outlet', 'Kisii Shop'
    ]
    for name in store_names:
        store = Store(
            name=name,
            address=fake.address(),
            location=fake.city(),
            description=fake.text(max_nb_chars=200)
        )
        db.session.add(store)
        stores.append(store)
    db.session.commit()

    # Link merchant to all stores
    for store in stores:
        merchant.stores.append(store)
    db.session.commit()

    # --- Users (Admins + Clerks) ---
    first_names = ['James', 'Sarah', 'Michael', 'Emily', 'David', 'Laura', 'Robert', 'Jessica']
    last_names = ['Smith', 'Johnson', 'Brown', 'Taylor', 'Wilson', 'Davis', 'Clark', 'Lewis']
    admins, clerks = [], []
    for store in stores:
        # Admins (at least 1, up to 3 per store)
        num_admins = max(1, random.randint(2, 3))  # Ensure at least 1 admin
        store_admins = []
        for i in range(num_admins):
            fn, ln = random.choice(first_names), random.choice(last_names)
            email = generate_unique_email(fn, ln, store.id, 'ADMIN', i + 1)
            admin = User(
                name=f"{fn} {ln}",
                email=email,
                role=UserRole.ADMIN,
                status=UserStatus.INACTIVE if i == 0 else UserStatus.ACTIVE,
                _password=generate_password_hash('password123')
            )
            admin.stores.append(store)
            store_admins.append(admin)
            admins.append(admin)
            db.session.add(admin)
        db.session.commit()

        # Clerks (at least 1, up to 5 per store, assigned to an admin)
        with db.session.no_autoflush:  # Prevent autoflush during manager_id query
            num_clerks = max(1, random.randint(3, 5))  # Ensure at least 1 clerk
            for j in range(num_clerks):
                fn, ln = random.choice(first_names), random.choice(last_names)
                email = generate_unique_email(fn, ln, store.id, 'CLERK', j + 1)
                clerk = User(
                    name=f"{fn} {ln}",
                    email=email,
                    role=UserRole.CLERK,
                    status=UserStatus.INACTIVE if j == 0 else UserStatus.ACTIVE,
                    _password=generate_password_hash('password123'),
                    manager_id=random.choice(store_admins).id
                )
                clerk.stores.append(store)
                clerks.append(clerk)
                db.session.add(clerk)
            db.session.commit()

    # --- Invitations ---
    print("📧 Generating invitations...")
    invitation_users = []
    current_date = datetime(2025, 5, 9)
    for store in stores:
        store_admins = [a for a in admins if any(s.id == store.id for s in a.stores)]
        if not store_admins:
            print(f"⚠️ No admins for store {store.name} (ID: {store.id}) - skipping invitations")
            continue
        # Admin Invitations (2-3 per store, created by merchant)
        for i in range(random.randint(2, 3)):
            fn, ln = random.choice(first_names), random.choice(last_names)
            email = generate_unique_email(fn, ln, store.id, 'ADMIN_INVITE', i + 2)
            status = random.choice([InvitationStatus.PENDING, InvitationStatus.ACCEPTED, InvitationStatus.EXPIRED])
            created_at = current_date - timedelta(days=random.randint(1, 10))
            invitation = Invitation(
                email=email,
                role=UserRole.ADMIN,
                creator_id=merchant.id,
                store_id=store.id,
                status=status,
                is_used=status == InvitationStatus.ACCEPTED,
                expires_at=created_at + timedelta(hours=24),
                created_at=created_at
            )
            db.session.add(invitation)
            db.session.flush()
            # Notification for invitation sent
            notification = Notification(
                user_id=merchant.id,
                message=f"Invitation sent to {email} for admin role at {store.name}.",
                type=NotificationType.USER_INVITED,
                related_entity_id=invitation.id,
                related_entity_type='Invitation',
                is_read=False,
                created_at=created_at,
                updated_at=created_at
            )
            db.session.add(notification)
            if status == InvitationStatus.ACCEPTED:
                admin = User(
                    name=f"{fn} {ln}",
                    email=email,
                    role=UserRole.ADMIN,
                    status=UserStatus.ACTIVE,
                    _password=generate_password_hash('password123')
                )
                admin.stores.append(store)
                invitation_users.append(admin)
                db.session.add(admin)
                notification = Notification(
                    user_id=merchant.id,
                    message=f"Invitation accepted by {email} for admin role at {store.name}.",
                    type=NotificationType.INVITATION,
                    related_entity_id=invitation.id,
                    related_entity_type='Invitation',
                    is_read=False,
                    created_at=created_at,
                    updated_at=created_at
                )
                db.session.add(notification)
        # Clerk Invitations (3-5 per store, created by a random admin)
        for i in range(random.randint(3, 5)):
            fn, ln = random.choice(first_names), random.choice(last_names)
            email = generate_unique_email(fn, ln, store.id, 'CLERK_INVITE', i + 3)
            status = random.choice([InvitationStatus.PENDING, InvitationStatus.ACCEPTED, InvitationStatus.EXPIRED])
            created_at = current_date - timedelta(days=random.randint(1, 10))
            creator = random.choice(store_admins)
            invitation = Invitation(
                email=email,
                role=UserRole.CLERK,
                creator_id=creator.id,
                store_id=store.id,
                status=status,
                is_used=status == InvitationStatus.ACCEPTED,
                expires_at=created_at + timedelta(hours=24),
                created_at=created_at
            )
            db.session.add(invitation)
            db.session.flush()
            # Notification for invitation sent
            notification = Notification(
                user_id=creator.id,
                message=f"Invitation sent to {email} for clerk role at {store.name}.",
                type=NotificationType.USER_INVITED,
                related_entity_id=invitation.id,
                related_entity_type='Invitation',
                is_read=False,
                created_at=created_at,
                updated_at=created_at
            )
            db.session.add(notification)
            if status == InvitationStatus.ACCEPTED:
                clerk = User(
                    name=f"{fn} {ln}",
                    email=email,
                    role=UserRole.CLERK,
                    status=UserStatus.ACTIVE,
                    _password=generate_password_hash('password123'),
                    manager_id=creator.id
                )
                clerk.stores.append(store)
                invitation_users.append(clerk)
                db.session.add(clerk)
                notification = Notification(
                    user_id=creator.id,
                    message=f"Invitation accepted by {email} for clerk role at {store.name}.",
                    type=NotificationType.INVITATION,
                    related_entity_id=invitation.id,
                    related_entity_type='Invitation',
                    is_read=False,
                    created_at=created_at,
                    updated_at=created_at
                )
                db.session.add(notification)
    db.session.commit()

    # --- Password Resets ---
    print("🔑 Generating password resets...")
    eligible_users = [u for u in admins + clerks + invitation_users if u.status == UserStatus.ACTIVE]
    for user in random.sample(eligible_users, min(5, len(eligible_users))):
        password_reset = PasswordReset(
            user_id=user.id,
            is_used=False,
            expires_at=current_date + timedelta(hours=24),
            created_at=current_date
        )
        db.session.add(password_reset)
    db.session.commit()

    # --- Categories ---
    categories = [
        ProductCategory(name='Groceries', description='Food & household essentials'),
        ProductCategory(name='Electronics', description='Gadgets and devices'),
        ProductCategory(name='Clothing', description='Apparel and accessories'),
        ProductCategory(name='Home Goods', description='Home and kitchen items'),
        ProductCategory(name='Beverages', description='Drinks and refreshments'),
        ProductCategory(name='Personal Care', description='Health and beauty products'),
    ]
    db.session.add_all(categories)
    db.session.commit()

    # --- Suppliers ---
    suppliers = []
    for _ in range(10):
        supplier = Supplier(
            name=fake.company(),
            email=fake.email(),
            phone=fake.phone_number(),
            address=fake.address()
        )
        suppliers.append(supplier)
    db.session.add_all(suppliers)
    db.session.commit()

    # --- Products ---
    products_data = [
        ('Basmati Rice 5kg', categories[0].id, 50, 800, 1200),
        ('Sugar 2kg', categories[0].id, 75, 200, 300),
        ('Wheat Flour 2kg', categories[0].id, 60, 150, 250),
        ('Sunflower Oil 1L', categories[0].id, 40, 250, 400),
        ('Milk 500ml', categories[4].id, 50, 60, 100),
        ('Toothpaste 100g', categories[5].id, 40, 150, 250),
        ('Detergent 1kg', categories[0].id, 60, 300, 450),
        ('Bread 400g', categories[0].id, 75, 50, 80),
        ('Socks 3pk', categories[2].id, 60, 150, 250),
        ('Towels 2pk', categories[3].id, 25, 400, 600),
        ('Batteries AA 4pk', categories[1].id, 70, 150, 250),
        ('Smartphone Charger', categories[1].id, 20, 500, 800),
    ]

    products_by_store = {}
    for store in stores:
        products_by_store[store.id] = []
        for idx, (name, cat_id, min_stock, buy_price, sell_price) in enumerate(products_data):
            stock = min_stock - random.randint(1, 5) if idx in [0, 1] else random.randint(min_stock, min_stock * 2)
            p = Product(
                name=name,
                sku=f"{name[:3].upper()}-{store.id}-{str(idx+1).zfill(2)}",
                category_id=cat_id,
                store_id=store.id,
                min_stock_level=min_stock,
                current_stock=stock,
                unit_price=sell_price
            )
            products_by_store[store.id].append(p)
            db.session.add(p)
        db.session.commit()

    # --- Sales Records ---
    print("💰 Generating sales records...")
    sales_by_store = {}
    start_date = datetime(2025, 1, 1)
    end_date = current_date
    for store in stores:
        sales_by_store[store.id] = []
        products = products_by_store[store.id]
        store_clerks = [c for c in clerks + invitation_users if c.role == UserRole.CLERK and any(s.id == store.id for s in c.stores)]
        if not store_clerks:
            print(f"⚠️ No clerks for store {store.name} (ID: {store.id}) - skipping sales records")
            continue
        current_date = start_date
        while current_date <= end_date:
            if random.random() < 0.9:
                daily_sales = random.randint(10, 30)
                for _ in range(daily_sales):
                    product = random.choice(products)
                    qty = random.randint(1, 5 if product.category_id == categories[1].id else 20)
                    if product.current_stock <= 0:
                        product.current_stock = random.randint(50, 100)
                    qty = min(qty, product.current_stock)
                    sale = SalesRecord(
                        product_id=product.id,
                        store_id=store.id,
                        quantity_sold=qty,
                        selling_price=product.unit_price,
                        sale_date=current_date,
                        recorded_by_id=random.choice([c.id for c in store_clerks]),
                        created_at=current_date,
                        updated_at=current_date
                    )
                    db.session.add(sale)
                    sales_by_store[store.id].append(sale)
                    product.current_stock -= qty
            current_date += timedelta(days=1)
            if current_date.day % 5 == 0:
                db.session.commit()
        db.session.commit()

    # --- Sales Growth ---
    print("📈 Generating sales growth data...")
    for store in stores:
        products = products_by_store[store.id]
        for month in range(1, 6):  # January to May 2025
            month_start = datetime(2025, month, 1)
            month_end = (month_start + timedelta(days=31)).replace(day=1) - timedelta(seconds=1)
            if month_end > end_date:
                month_end = end_date
            # Store-level growth
            total_revenue = db.session.query(
                func.coalesce(func.sum(SalesRecord.quantity_sold * SalesRecord.selling_price), 0)
            ).filter(
                SalesRecord.store_id == store.id,
                SalesRecord.sale_date.between(month_start, month_end)
            ).scalar() or 0.0
            prev_revenue = db.session.query(
                func.coalesce(func.sum(SalesRecord.quantity_sold * SalesRecord.selling_price), 0)
            ).filter(
                SalesRecord.store_id == store.id,
                SalesRecord.sale_date.between(
                    month_start - timedelta(days=31),
                    month_start - timedelta(seconds=1)
                )
            ).scalar() or 0.0
            growth = ((total_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else None
            sales_growth = SalesGrowth(
                store_id=store.id,
                product_id=None,
                month=month_start.date(),
                revenue=total_revenue,
                growth_percentage=growth,
                created_at=month_end,
                updated_at=month_end
            )
            db.session.add(sales_growth)
            # Product-level growth
            for product in products:
                product_revenue = db.session.query(
                    func.coalesce(func.sum(SalesRecord.quantity_sold * SalesRecord.selling_price), 0)
                ).filter(
                    SalesRecord.product_id == product.id,
                    SalesRecord.sale_date.between(month_start, month_end)
                ).scalar() or 0.0
                prev_product_revenue = db.session.query(
                    func.coalesce(func.sum(SalesRecord.quantity_sold * SalesRecord.selling_price), 0)
                ).filter(
                    SalesRecord.product_id == product.id,
                    SalesRecord.sale_date.between(
                        month_start - timedelta(days=31),
                        month_start - timedelta(seconds=1)
                    )
                ).scalar() or 0.0
                growth = ((product_revenue - prev_product_revenue) / prev_product_revenue * 100) if prev_product_revenue > 0 else None
                sales_growth = SalesGrowth(
                    store_id=store.id,
                    product_id=product.id,
                    month=month_start.date(),
                    revenue=product_revenue,
                    growth_percentage=growth,
                    created_at=month_end,
                    updated_at=month_end
                )
                db.session.add(sales_growth)
        db.session.commit()

    # --- Inventory Entries ---
    print("📦 Generating inventory entries...")
    supplier_assignments = defaultdict(lambda: defaultdict(set))
    for store in stores:
        products = products_by_store[store.id]
        store_clerks = [c for c in clerks + invitation_users if c.role == UserRole.CLERK and any(s.id == store.id for s in c.stores)]
        store_admins = [a for a in admins + invitation_users if a.role == UserRole.ADMIN and any(s.id == store.id for s in a.stores)]
        if not store_clerks:
            print(f"⚠️ No clerks for store {store.name} (ID: {store.id}) - skipping inventory entries")
            continue
        if not store_admins:
            print(f"⚠️ No admins for store {store.name} (ID: {store.id}) - notifications may only go to merchant")
        current_date = start_date
        while current_date <= end_date:
            if random.random() < 0.7 and (current_date - start_date).days % 5 == 0:
                for product in products:
                    supplier = random.choice(suppliers)
                    qty_received = random.randint(50, 200)
                    spoilage_rate = 0.25 if product.category_id == categories[0].id else 0.1 if product.category_id == categories[2].id else 0.05
                    qty_spoiled = int(qty_received * spoilage_rate) if random.random() < 0.3 else 0
                    buy_price = next(p[3] for p in products_data if p[0] == product.name)
                    sell_price = product.unit_price
                    payment_status = PaymentStatus.PAID if random.random() < 0.55 else PaymentStatus.UNPAID
                    payment_date = current_date if payment_status == PaymentStatus.PAID else None
                    entry = InventoryEntry(
                        product_id=product.id,
                        store_id=store.id,
                        category_id=product.category_id,
                        quantity_received=qty_received,
                        quantity_spoiled=qty_spoiled,
                        buying_price=buy_price,
                        selling_price=sell_price,
                        payment_status=payment_status,
                        payment_date=payment_date,
                        supplier_id=supplier.id,
                        recorded_by=random.choice([c.id for c in store_clerks]),
                        entry_date=current_date,
                        due_date=current_date + timedelta(days=random.randint(15, 30)),
                        created_at=current_date,
                        updated_at=current_date
                    )
                    db.session.add(entry)
                    db.session.flush()
                    supplier_assignments[supplier.id][store.id].add(product.id)
                    product.current_stock += (qty_received - qty_spoiled)
                    if product.current_stock <= product.min_stock_level:
                        # Notify clerks and admins (if available), fall back to merchant
                        recipients = store_clerks + (store_admins if store_admins else [merchant])
                        for user in recipients:
                            notification = Notification(
                                user_id=user.id,
                                message=f"Product '{product.name}' at store '{store.name}' is low on stock: {product.current_stock} units.",
                                type=NotificationType.LOW_STOCK,
                                related_entity_id=product.id,
                                related_entity_type='Product',
                                is_read=False,
                                created_at=current_date,
                                updated_at=current_date
                            )
                            db.session.add(notification)
                    if qty_spoiled > 0:
                        # Notify merchant and admins (if available)
                        recipients = [merchant] + (store_admins if store_admins else [])
                        for user in recipients:
                            notification = Notification(
                                user_id=user.id,
                                message=f"Spoilage detected for '{product.name}' at store '{store.name}': {qty_spoiled} units, value {qty_spoiled * sell_price} KSh.",
                                type=NotificationType.SPOILAGE,
                                related_entity_id=entry.id,
                                related_entity_type='InventoryEntry',
                                is_read=False,
                                created_at=current_date,
                                updated_at=current_date
                            )
                            db.session.add(notification)
                    if payment_status == PaymentStatus.PAID and store_admins:
                        audit = PaymentAudit(
                            inventory_entry_id=entry.id,
                            supplier_id=supplier.id,
                            user_id=random.choice([a.id for a in store_admins]),
                            old_status=PaymentStatus.UNPAID,
                            new_status=PaymentStatus.PAID,
                            change_date=current_date,
                            created_at=current_date,
                            updated_at=current_date
                        )
                        db.session.add(audit)
            current_date += timedelta(days=1)
        db.session.commit()

    # --- Supply Requests ---
    print("📋 Generating supply requests...")
    for store in stores:
        products = products_by_store[store.id]
        store_clerks = [c for c in clerks + invitation_users if c.role == UserRole.CLERK and any(s.id == store.id for s in c.stores)]
        store_admins = [a for a in admins + invitation_users if a.role == UserRole.ADMIN and any(s.id == store.id for s in a.stores)]
        if not store_clerks:
            print(f"⚠️ No clerks for store {store.name} (ID: {store.id}) - skipping supply requests")
            continue
        current_date = start_date
        while current_date <= end_date:
            if random.random() < 0.4:
                product = random.choice(products)
                clerk = random.choice(store_clerks)
                status = random.choice(list(RequestStatus))
                supply_request = SupplyRequest(
                    product_id=product.id,
                    store_id=store.id,
                    quantity_requested=random.randint(20, 100),
                    clerk_id=clerk.id,
                    admin_id=random.choice([a.id for a in store_admins]) if status != RequestStatus.PENDING and store_admins else None,
                    status=status,
                    decline_reason=fake.sentence() if status == RequestStatus.DECLINED else None,
                    approval_date=current_date if status in [RequestStatus.APPROVED, RequestStatus.DECLINED] else None,
                    created_at=current_date,
                    updated_at=current_date
                )
                db.session.add(supply_request)
                db.session.flush()
                if status == RequestStatus.PENDING and store_admins:
                    for admin in store_admins:
                        notification = Notification(
                            user_id=admin.id,
                            message=f"New supply request for {product.name} by clerk {clerk.name} at store {store.name}.",
                            type=NotificationType.SUPPLY_REQUEST,
                            related_entity_id=supply_request.id,
                            related_entity_type='SupplyRequest',
                            is_read=False,
                            created_at=current_date,
                            updated_at=current_date
                        )
                        db.session.add(notification)
                if status in [RequestStatus.APPROVED, RequestStatus.DECLINED]:
                    message = f"Your supply request for {product.name} at store {store.name} has been {status.value.lower()}."
                    if status == RequestStatus.DECLINED:
                        message += f" Reason: {supply_request.decline_reason}"
                    notification = Notification(
                        user_id=clerk.id,
                        message=message,
                        type=NotificationType.SUPPLY_REQUEST,
                        related_entity_id=supply_request.id,
                        related_entity_type='SupplyRequest',
                        is_read=False,
                        created_at=current_date,
                        updated_at=current_date
                    )
                    db.session.add(notification)
            current_date += timedelta(days=1)
        db.session.commit()

    # --- Account Status Changes ---
    print("🔄 Generating account status changes...")
    for store in stores:
        store_clerks = [c for c in clerks + invitation_users if c.role == UserRole.CLERK and any(s.id == store.id for s in c.stores) and c.status == UserStatus.ACTIVE]
        store_admins = [a for a in admins + invitation_users if a.role == UserRole.ADMIN and any(s.id == store.id for s in a.stores) and a.status == UserStatus.ACTIVE]
        # Deactivate one clerk
        if store_clerks:
            clerk_to_deactivate = random.choice(store_clerks)
            clerk_to_deactivate.status = UserStatus.INACTIVE
            db.session.add(clerk_to_deactivate)
            notification = Notification(
                user_id=clerk_to_deactivate.id,
                message=f"Your account for store {store.name} has been deactivated.",
                type=NotificationType.ACCOUNT_STATUS,
                related_entity_id=clerk_to_deactivate.id,
                related_entity_type='User',
                is_read=False,
                created_at=end_date,
                updated_at=end_date
            )
            db.session.add(notification)
            recipients = [merchant] + (store_admins if store_admins else [])
            for user in recipients:
                if User.query.get(user.id):  # Verify user exists
                    notification = Notification(
                        user_id=user.id,
                        message=f"Clerk {clerk_to_deactivate.name}'s account for store {store.name} has been deactivated.",
                        type=NotificationType.ACCOUNT_STATUS,
                        related_entity_id=clerk_to_deactivate.id,
                        related_entity_type='User',
                        is_read=False,
                        created_at=end_date,
                        updated_at=end_date
                    )
                    db.session.add(notification)
        # Activate one inactive admin
        inactive_admins = [a for a in admins + invitation_users if a.role == UserRole.ADMIN and any(s.id == store.id for s in a.stores) and a.status == UserStatus.INACTIVE]
        if inactive_admins:
            admin_to_activate = random.choice(inactive_admins)
            admin_to_activate.status = UserStatus.ACTIVE
            db.session.add(admin_to_activate)
            notification = Notification(
                user_id=admin_to_activate.id,
                message=f"Your account for store {store.name} has been activated.",
                type=NotificationType.ACCOUNT_STATUS,
                related_entity_id=admin_to_activate.id,
                related_entity_type='User',
                is_read=False,
                created_at=end_date,
                updated_at=end_date
            )
            db.session.add(notification)
            recipients = [merchant]
            for user in recipients:
                if User.query.get(user.id):  # Verify user exists
                    notification = Notification(
                        user_id=user.id,
                        message=f"Admin {admin_to_activate.name}'s account for store {store.name} has been activated.",
                        type=NotificationType.ACCOUNT_STATUS,
                        related_entity_id=admin_to_activate.id,
                        related_entity_type='User',
                        is_read=False,
                        created_at=end_date,
                        updated_at=end_date
                    )
                    db.session.add(notification)
    db.session.commit()

    # --- Account Deletions ---
    print("🗑️ Generating account deletions...")
    for store in stores:
        store_clerks = [c for c in clerks + invitation_users if c.role == UserRole.CLERK and any(s.id == store.id for s in c.stores) and c.status == UserStatus.ACTIVE]
        store_admins = [a for a in admins + invitation_users if a.role == UserRole.ADMIN and any(s.id == store.id for s in a.stores) and a.status == UserStatus.ACTIVE]
        # Delete one active clerk per store
        if store_clerks:
            clerk_to_delete = random.choice(store_clerks)
            print(f"Deleting clerk {clerk_to_delete.name} (ID: {clerk_to_delete.id}) for store {store.name}")
            # Reassign InventoryEntry recorded_by to merchant
            InventoryEntry.query.filter_by(recorded_by=clerk_to_delete.id).update({'recorded_by': merchant.id, 'updated_at': end_date})
            # Delete related records to avoid NOT NULL violations
            PasswordReset.query.filter_by(user_id=clerk_to_delete.id).delete()
            Notification.query.filter_by(user_id=clerk_to_delete.id).delete()
            SupplyRequest.query.filter_by(clerk_id=clerk_to_delete.id).delete()
            SalesRecord.query.filter_by(recorded_by_id=clerk_to_delete.id).delete()
            PaymentAudit.query.filter_by(user_id=clerk_to_delete.id).delete()
            Invitation.query.filter_by(creator_id=clerk_to_delete.id).delete()
            # Generate system-wide notification for deletion
            notification = Notification(
                user_id=None,  # System-wide notification
                message=f"Clerk {clerk_to_delete.name}'s account for store {store.name} has been deleted.",
                type=NotificationType.ACCOUNT_DELETION,
                related_entity_id=clerk_to_delete.id,
                related_entity_type='User',
                is_read=False,
                created_at=end_date,
                updated_at=end_date
            )
            db.session.add(notification)
            # Notify merchant and admins
            recipients = [merchant] + (store_admins if store_admins else [])
            for user in recipients:
                if User.query.get(user.id):  # Verify user exists
                    notification = Notification(
                        user_id=user.id,
                        message=f"Clerk {clerk_to_delete.name}'s account for store {store.name} has been deleted.",
                        type=NotificationType.ACCOUNT_DELETION,
                        related_entity_id=clerk_to_delete.id,
                        related_entity_type='User',
                        is_read=False,
                        created_at=end_date,
                        updated_at=end_date
                    )
                    db.session.add(notification)
            db.session.delete(clerk_to_delete)
            db.session.commit()
        # Delete one active admin per store, if available
        if store_admins:
            admin_to_delete = random.choice(store_admins)
            print(f"Deleting admin {admin_to_delete.name} (ID: {admin_to_delete.id}) for store {store.name}")
            # Reassign InventoryEntry recorded_by to merchant
            InventoryEntry.query.filter_by(recorded_by=admin_to_delete.id).update({'recorded_by': merchant.id, 'updated_at': end_date})
            # Delete related records
            PasswordReset.query.filter_by(user_id=admin_to_delete.id).delete()
            Notification.query.filter_by(user_id=admin_to_delete.id).delete()
            SupplyRequest.query.filter_by(admin_id=admin_to_delete.id).update({'admin_id': None})
            PaymentAudit.query.filter_by(user_id=admin_to_delete.id).delete()
            Invitation.query.filter_by(creator_id=admin_to_delete.id).delete()
            # Reassign clerks managed by this admin
            User.query.filter_by(manager_id=admin_to_delete.id).update({'manager_id': None})
            # Generate system-wide notification for deletion
            notification = Notification(
                user_id=None,  # System-wide notification
                message=f"Admin {admin_to_delete.name}'s account for store {store.name} has been deleted.",
                type=NotificationType.ACCOUNT_DELETION,
                related_entity_id=admin_to_delete.id,
                related_entity_type='User',
                is_read=False,
                created_at=end_date,
                updated_at=end_date
            )
            db.session.add(notification)
            # Notify merchant and remaining admins
            recipients = [merchant] + [a for a in store_admins if a.id != admin_to_delete.id]
            for user in recipients:
                if User.query.get(user.id):  # Verify user exists
                    notification = Notification(
                        user_id=user.id,
                        message=f"Admin {admin_to_delete.name}'s account for store {store.name} has been deleted.",
                        type=NotificationType.ACCOUNT_DELETION,
                        related_entity_id=admin_to_delete.id,
                        related_entity_type='User',
                        is_read=False,
                        created_at=end_date,
                        updated_at=end_date
                    )
                    db.session.add(notification)
            db.session.delete(admin_to_delete)
            db.session.commit()

    # --- Payment Status Updates ---
    print("💸 Generating payment status updates...")
    for store in stores:
        store_admins = User.query.filter(
            User.role == UserRole.ADMIN,
            User.status == UserStatus.ACTIVE,
            User.stores.any(id=store.id)
        ).all()
        if not store_admins:
            print(f"⚠️ No active admins for store {store.name} (ID: {store.id}) - skipping payment status updates")
            continue
        unpaid_entries = InventoryEntry.query.filter_by(store_id=store.id, payment_status=PaymentStatus.UNPAID).all()
        for entry in random.sample(unpaid_entries, min(3, len(unpaid_entries))):
            entry.payment_status = PaymentStatus.PAID
            entry.payment_date = end_date
            db.session.add(entry)
            supplier = Supplier.query.get(entry.supplier_id) if entry.supplier_id else None
            product = Product.query.get(entry.product_id)
            audit = PaymentAudit(
                inventory_entry_id=entry.id,
                supplier_id=supplier.id if supplier else None,
                user_id=random.choice([a.id for a in store_admins]),
                old_status=PaymentStatus.UNPAID,
                new_status=PaymentStatus.PAID,
                change_date=end_date,
                created_at=end_date,
                updated_at=end_date
            )
            db.session.add(audit)
            # Notify merchant and active admins
            recipients = [merchant] + store_admins
            for user in recipients:
                if User.query.get(user.id):  # Verify user exists
                    supplier_name = supplier.name if supplier else "Unknown Supplier"
                    notification = Notification(
                        user_id=user.id,
                        message=f"Payment of {entry.quantity_received * entry.buying_price} KSh to supplier {supplier_name} for {product.name} at store {store.name} marked as paid.",
                        type=NotificationType.PAYMENT,
                        related_entity_id=entry.id,
                        related_entity_type='InventoryEntry',
                        is_read=False,
                        created_at=end_date,
                        updated_at=end_date
                    )
                    db.session.add(notification)
        db.session.commit()

    print("✅ Database seeded successfully!")
    print(f"📊 Stats:")
    print(f"- Stores: {len(stores)}")
    print(f"- Products: {sum(len(p) for p in products_by_store.values())}")
    print(f"- Sales Records: {db.session.query(func.count(SalesRecord.id)).scalar()}")
    print(f"- Inventory Entries: {db.session.query(func.count(InventoryEntry.id)).scalar()}")
    print(f"- Supply Requests: {db.session.query(func.count(SupplyRequest.id)).scalar()}")
    print(f"- Notifications: {db.session.query(func.count(Notification.id)).scalar()}")
    print(f"- Invitations: {db.session.query(func.count(Invitation.id)).scalar()}")
    print(f"- Password Resets: {db.session.query(func.count(PasswordReset.id)).scalar()}")
    print(f"- Payment Audits: {db.session.query(func.count(PaymentAudit.id)).scalar()}")
    print(f"- Sales Growth: {db.session.query(func.count(SalesGrowth.id)).scalar()}")
    print(f"- Users: {db.session.query(func.count(User.id)).scalar()}")
    print(f"- Admins: {len(admins) + sum(1 for u in invitation_users if u.role == UserRole.ADMIN)}")
    print(f"- Clerks: {len(clerks) + sum(1 for u in invitation_users if u.role == UserRole.CLERK)}")

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        try:
            ensure_tables_exist()
            clear_existing_data()
            seed_database()
        except Exception as e:
            print(f"❌ Seeding failed: {e}")
            db.session.rollback()
            raise