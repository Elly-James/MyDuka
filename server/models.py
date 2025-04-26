from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime
import enum
import uuid

from extensions import db

class UserRole(enum.Enum):
    MERCHANT = 'merchant'
    ADMIN = 'admin'
    CLERK = 'clerk'

class UserStatus(enum.Enum):
    ACTIVE = 'active'
    INACTIVE = 'inactive'

class User(db.Model):
    """User model for all system users (merchants, admins, clerks)"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    _password = db.Column('password', db.String(255), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False)
    status = db.Column(db.Enum(UserStatus), default=UserStatus.ACTIVE)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    invitations = db.relationship('Invitation', backref='created_by', lazy=True)
    supply_requests = db.relationship('SupplyRequest', backref='requested_by', foreign_keys='SupplyRequest.clerk_id', lazy=True)
    processed_requests = db.relationship('SupplyRequest', backref='processed_by', foreign_keys='SupplyRequest.admin_id', lazy=True)
    inventory_entries = db.relationship('InventoryEntry', backref='clerk', lazy=True)
    store = db.relationship('Store', backref='users')

    @hybrid_property
    def password(self):
        return self._password

    @password.setter
    def password(self, password):
        self._password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self._password, password)

    def __repr__(self):
        return f'<User {self.email}>'

class Invitation(db.Model):
    """Invitation model for admin and clerk registration"""
    __tablename__ = 'invitations'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    token = db.Column(db.String(255), unique=True, nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=True)
    is_used = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    store = db.relationship('Store', backref='invitations')

    def __repr__(self):
        return f'<Invitation {self.email}>'

class Store(db.Model):
    """Store model for different merchant locations"""
    __tablename__ = 'stores'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    products = db.relationship('Product', backref='store', lazy=True)
    
    def __repr__(self):
        return f'<Store {self.name}>'

class ProductCategory(db.Model):
    """Product categories"""
    __tablename__ = 'product_categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # Relationships
    products = db.relationship('Product', backref='category', lazy=True)
    
    def __repr__(self):
        return f'<ProductCategory {self.name}>'

class Product(db.Model):
    """Product model for inventory items"""
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    sku = db.Column(db.String(50), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('product_categories.id'), nullable=True)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False)
    current_stock = db.Column(db.Integer, default=0)
    min_stock_level = db.Column(db.Integer, default=5)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    inventory_entries = db.relationship('InventoryEntry', backref='product', lazy=True)
    supply_requests = db.relationship('SupplyRequest', backref='product', lazy=True)
    
    def __repr__(self):
        return f'<Product {self.name}>'

class Supplier(db.Model):
    """Supplier model"""
    __tablename__ = 'suppliers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact_person = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    inventory_entries = db.relationship('InventoryEntry', backref='supplier', lazy=True)
    
    def __repr__(self):
        return f'<Supplier {self.name}>'

class PaymentStatus(enum.Enum):
    PAID = 'paid'
    UNPAID = 'unpaid'

class InventoryEntry(db.Model):
    """Inventory entry for stock movements"""
    __tablename__ = 'inventory_entries'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity_received = db.Column(db.Integer, nullable=False)
    quantity_spoiled = db.Column(db.Integer, default=0)
    buying_price = db.Column(db.Float, nullable=False)
    selling_price = db.Column(db.Float, nullable=False)
    payment_status = db.Column(db.Enum(PaymentStatus), default=PaymentStatus.UNPAID)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=True)
    recorded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    entry_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<InventoryEntry {self.product_id} - {self.quantity_received}>'

class RequestStatus(enum.Enum):
    PENDING = 'pending'
    APPROVED = 'approved'
    DECLINED = 'declined'

class SupplyRequest(db.Model):
    """Supply request model"""
    __tablename__ = 'supply_requests'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity_requested = db.Column(db.Integer, nullable=False)
    clerk_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.Enum(RequestStatus), default=RequestStatus.PENDING)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    decline_reason = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<SupplyRequest {self.product_id} - {self.quantity_requested}>'