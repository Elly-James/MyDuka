from datetime import datetime
import enum
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.ext.hybrid import hybrid_property
from extensions import db

class UserRole(enum.Enum):
    MERCHANT = 'merchant'
    ADMIN = 'admin'
    CLERK = 'clerk'

class UserStatus(enum.Enum):
    ACTIVE = 'active'
    INACTIVE = 'inactive'

class PaymentStatus(enum.Enum):
    PAID = 'paid'
    UNPAID = 'unpaid'

class RequestStatus(enum.Enum):
    PENDING = 'pending'
    APPROVED = 'approved'
    DECLINED = 'declined'

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

    store = db.relationship('Store', back_populates='users')
    invitations = db.relationship('Invitation', back_populates='creator')
    inventory_entries = db.relationship('InventoryEntry', back_populates='clerk')
    supply_requests = db.relationship('SupplyRequest', back_populates='clerk', foreign_keys='SupplyRequest.clerk_id')
    approved_requests = db.relationship('SupplyRequest', back_populates='admin', foreign_keys='SupplyRequest.admin_id')
    password_resets = db.relationship('PasswordReset', back_populates='user')
    notifications = db.relationship('Notification', back_populates='user')

    @hybrid_property
    def password(self):
        return self._password

    @password.setter
    def password(self, password):
        self._password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self._password, password)

class Store(db.Model):
    """Store model for business locations"""
    __tablename__ = 'stores'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    users = db.relationship('User', back_populates='store')
    products = db.relationship('Product', back_populates='store')
    invitations = db.relationship('Invitation', back_populates='store')

class ProductCategory(db.Model):
    """Product category model"""
    __tablename__ = 'product_categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    products = db.relationship('Product', back_populates='category')

class Product(db.Model):
    """Product model for inventory items"""
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    sku = db.Column(db.String(50), unique=True, nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('product_categories.id'), nullable=True)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False)
    current_stock = db.Column(db.Integer, default=0)
    min_stock_level = db.Column(db.Integer, default=5)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    category = db.relationship('ProductCategory', back_populates='products')
    store = db.relationship('Store', back_populates='products')
    inventory_entries = db.relationship('InventoryEntry', back_populates='product')
    supply_requests = db.relationship('SupplyRequest', back_populates='product')

    __table_args__ = (
        db.Index('idx_product_store', 'store_id'),
        db.Index('idx_product_category', 'category_id'),
    )

class Supplier(db.Model):
    """Supplier model for inventory sources"""
    __tablename__ = 'suppliers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    inventory_entries = db.relationship('InventoryEntry', back_populates='supplier')

class InventoryEntry(db.Model):
    """Inventory entry model for stock records"""
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

    product = db.relationship('Product', back_populates='inventory_entries')
    supplier = db.relationship('Supplier', back_populates='inventory_entries')
    clerk = db.relationship('User', back_populates='inventory_entries')

    __table_args__ = (
        db.Index('idx_entry_product', 'product_id'),
        db.Index('idx_entry_date', 'entry_date'),
    )

class SupplyRequest(db.Model):
    """Supply request model for restocking requests"""
    __tablename__ = 'supply_requests'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity_requested = db.Column(db.Integer, nullable=False)
    clerk_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    status = db.Column(db.Enum(RequestStatus), default=RequestStatus.PENDING)
    decline_reason = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = db.relationship('Product', back_populates='supply_requests')
    clerk = db.relationship('User', back_populates='supply_requests', foreign_keys=[clerk_id])
    admin = db.relationship('User', back_populates='approved_requests', foreign_keys=[admin_id])

class Invitation(db.Model):
    """Invitation model for user registration"""
    __tablename__ = 'invitations'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    token = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    role = db.Column(db.Enum(UserRole), nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=True)
    is_used = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    creator = db.relationship('User', back_populates='invitations')
    store = db.relationship('Store', back_populates='invitations')

class PasswordReset(db.Model):
    """Password reset model for user password recovery"""
    __tablename__ = 'password_resets'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    is_used = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', back_populates='password_resets')

class Notification(db.Model):
    """Notification model for user notifications"""
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', back_populates='notifications')