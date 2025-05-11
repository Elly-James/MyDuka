from datetime import datetime, timedelta
import enum
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.ext.hybrid import hybrid_property
from extensions import db

# Association table for many-to-many user-store relationship
user_store = db.Table(
    'user_store',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('store_id', db.Integer, db.ForeignKey('stores.id'), primary_key=True),
    db.Index('idx_user_store', 'user_id', 'store_id')
)

class UserRole(enum.Enum):
    MERCHANT = 'MERCHANT'
    ADMIN = 'ADMIN'
    CLERK = 'CLERK'

class UserStatus(enum.Enum):
    ACTIVE = 'ACTIVE'
    INACTIVE = 'INACTIVE'

class PaymentStatus(enum.Enum):
    PAID = 'PAID'
    UNPAID = 'UNPAID'

class RequestStatus(enum.Enum):
    PENDING = 'PENDING'
    APPROVED = 'DECLINED'
    DECLINED = 'DECLINED'

class InvitationStatus(enum.Enum):
    PENDING = 'PENDING'
    ACCEPTED = 'ACCEPTED'
    EXPIRED = 'EXPIRED'

class NotificationType(enum.Enum):
    INVITATION = 'INVITATION'
    LOW_STOCK = 'LOW_STOCK'
    SUPPLY_REQUEST = 'SUPPLY_REQUEST'
    SPOILAGE = 'SPOILAGE'
    PAYMENT = 'PAYMENT'
    ACCOUNT_STATUS = 'ACCOUNT_STATUS'
    ACCOUNT_DELETION = 'ACCOUNT_DELETION'
    USER_INVITED = 'USER_INVITED'

class User(db.Model):
    """User model for all system users (merchants, admins, clerks)"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    _password = db.Column('password', db.String(255), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False)
    status = db.Column(db.Enum(UserStatus), default=UserStatus.ACTIVE, nullable=False)
    manager_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    stores = db.relationship('Store', secondary=user_store, back_populates='users')
    manager = db.relationship('User', remote_side=[id], back_populates='clerks')
    clerks = db.relationship('User', back_populates='manager')
    invitations = db.relationship('Invitation', back_populates='creator')
    inventory_entries = db.relationship('InventoryEntry', back_populates='clerk')
    supply_requests = db.relationship('SupplyRequest', back_populates='clerk', foreign_keys='SupplyRequest.clerk_id')
    approved_requests = db.relationship('SupplyRequest', back_populates='admin', foreign_keys='SupplyRequest.admin_id')
    password_resets = db.relationship('PasswordReset', back_populates='user')
    notifications = db.relationship('Notification', back_populates='user')
    sales_records = db.relationship('SalesRecord', back_populates='recorded_by')
    payment_audits = db.relationship('PaymentAudit', back_populates='user')

    __table_args__ = (
        db.Index('idx_user_email', 'email'),
        db.Index('idx_user_role', 'role'),
        db.Index('idx_user_manager', 'manager_id'),
    )

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
    location = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    users = db.relationship('User', secondary=user_store, back_populates='stores')
    products = db.relationship('Product', back_populates='store')
    invitations = db.relationship('Invitation', back_populates='store')
    sales_records = db.relationship('SalesRecord', back_populates='store')
    inventory_entries = db.relationship('InventoryEntry', back_populates='store')
    supply_requests = db.relationship('SupplyRequest', back_populates='store')
    sales_growths = db.relationship('SalesGrowth', back_populates='store')

    __table_args__ = (
        db.Index('idx_store_name', 'name'),
    )

class ProductCategory(db.Model):
    """Product category model"""
    __tablename__ = 'product_categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    products = db.relationship('Product', back_populates='category')
    inventory_entries = db.relationship('InventoryEntry', back_populates='category')

class Product(db.Model):
    """Product model for inventory items"""
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    sku = db.Column(db.String(50), unique=True, nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('product_categories.id'), nullable=True)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False)
    current_stock = db.Column(db.Integer, default=0, nullable=False)
    min_stock_level = db.Column(db.Integer, default=5, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    category = db.relationship('ProductCategory', back_populates='products')
    store = db.relationship('Store', back_populates='products')
    inventory_entries = db.relationship('InventoryEntry', back_populates='product')
    supply_requests = db.relationship('SupplyRequest', back_populates='product')
    sales_records = db.relationship('SalesRecord', back_populates='product')
    sales_growths = db.relationship('SalesGrowth', back_populates='product')

    __table_args__ = (
        db.Index('idx_product_store', 'store_id'),
        db.Index('idx_product_category', 'category_id'),
        db.Index('idx_product_stock', 'current_stock'),
    )

    @hybrid_property
    def is_low_stock(self):
        return self.current_stock <= self.min_stock_level

class Supplier(db.Model):
    """Supplier model for inventory sources"""
    __tablename__ = 'suppliers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    inventory_entries = db.relationship('InventoryEntry', back_populates='supplier')
    payment_audits = db.relationship('PaymentAudit', back_populates='supplier')

class InventoryEntry(db.Model):
    """Inventory entry model for stock records"""
    __tablename__ = 'inventory_entries'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('product_categories.id'), nullable=True)
    quantity_received = db.Column(db.Integer, nullable=False)
    quantity_spoiled = db.Column(db.Integer, default=0, nullable=False)
    buying_price = db.Column(db.Float, nullable=False)
    selling_price = db.Column(db.Float, nullable=False)
    payment_status = db.Column(db.Enum(PaymentStatus), default=PaymentStatus.UNPAID, nullable=False)
    payment_date = db.Column(db.DateTime, nullable=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=True)
    recorded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    entry_date = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    product = db.relationship('Product', back_populates='inventory_entries')
    category = db.relationship('ProductCategory', back_populates='inventory_entries')
    supplier = db.relationship('Supplier', back_populates='inventory_entries')
    clerk = db.relationship('User', back_populates='inventory_entries')
    store = db.relationship('Store', back_populates='inventory_entries')
    payment_audits = db.relationship('PaymentAudit', back_populates='inventory_entry')

    __table_args__ = (
        db.Index('idx_entry_product', 'product_id'),
        db.Index('idx_entry_date', 'entry_date'),
        db.Index('idx_entry_store', 'store_id'),
        db.Index('idx_entry_payment', 'payment_status'),
        db.Index('idx_entry_category', 'category_id'),
    )

    @hybrid_property
    def spoilage_value(self):
        return self.quantity_spoiled * self.selling_price

    @hybrid_property
    def spoilage_percentage(self):
        return (self.quantity_spoiled / self.quantity_received * 100) if self.quantity_received > 0 else 0

class SalesRecord(db.Model):
    """Sales record model for tracking product sales"""
    __tablename__ = 'sales_records'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False)
    quantity_sold = db.Column(db.Integer, nullable=False)
    selling_price = db.Column(db.Float, nullable=False)
    sale_date = db.Column(db.DateTime, default=datetime.utcnow)
    recorded_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    product = db.relationship('Product', back_populates='sales_records')
    store = db.relationship('Store', back_populates='sales_records')
    recorded_by = db.relationship('User', back_populates='sales_records')

    __table_args__ = (
        db.Index('idx_sales_product', 'product_id'),
        db.Index('idx_sales_store', 'store_id'),
        db.Index('idx_sales_date', 'sale_date'),
        db.Index('idx_sales_recorded_by', 'recorded_by_id'),
    )

    @hybrid_property
    def revenue(self):
        return self.quantity_sold * self.selling_price

class SupplyRequest(db.Model):
    """Supply request model for restocking requests"""
    __tablename__ = 'supply_requests'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False)
    quantity_requested = db.Column(db.Integer, nullable=False)
    clerk_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    status = db.Column(db.Enum(RequestStatus), default=RequestStatus.PENDING, nullable=False)
    decline_reason = db.Column(db.Text, nullable=True)
    approval_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    product = db.relationship('Product', back_populates='supply_requests')
    store = db.relationship('Store', back_populates='supply_requests')
    clerk = db.relationship('User', back_populates='supply_requests', foreign_keys=[clerk_id])
    admin = db.relationship('User', back_populates='approved_requests', foreign_keys=[admin_id])

    __table_args__ = (
        db.Index('idx_supply_request_status', 'status'),
        db.Index('idx_supply_request_store', 'store_id'),
    )

class Invitation(db.Model):
    """Invitation model for user registration"""
    __tablename__ = 'invitations'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    token = db.Column(db.String(255), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    role = db.Column(db.Enum(UserRole), nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)  # Changed to nullable=True
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False)
    status = db.Column(db.Enum(InvitationStatus), default=InvitationStatus.PENDING, nullable=False)
    is_used = db.Column(db.Boolean, default=False, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.utcnow() + timedelta(hours=24))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    creator = db.relationship('User', back_populates='invitations')
    store = db.relationship('Store', back_populates='invitations')

    __table_args__ = (
        db.Index('idx_invitation_token', 'token'),
        db.Index('idx_invitation_status', 'status'),
    )

    def check_expiry(self):
        """Update status to EXPIRED if past expiration time"""
        if self.status == InvitationStatus.PENDING and datetime.utcnow() > self.expires_at:
            self.status = InvitationStatus.EXPIRED
            self.updated_at = datetime.utcnow()

class PasswordReset(db.Model):
    """Password reset model for user password recovery"""
    __tablename__ = 'password_resets'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    is_used = db.Column(db.Boolean, default=False, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', back_populates='password_resets')

class Notification(db.Model):
    """Notification model for user notifications"""
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Already nullable
    message = db.Column(db.String(500), nullable=False)
    type = db.Column(db.Enum(NotificationType), nullable=False)
    related_entity_id = db.Column(db.Integer, nullable=True)
    related_entity_type = db.Column(db.String(50), nullable=True)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', back_populates='notifications')

    __table_args__ = (
        db.Index('idx_notification_user_read', 'user_id', 'is_read'),
        db.Index('idx_notification_type', 'type'),
    )

class PaymentAudit(db.Model):
    """Payment audit model for tracking payment status changes"""
    __tablename__ = 'payment_audits'

    id = db.Column(db.Integer, primary_key=True)
    inventory_entry_id = db.Column(db.Integer, db.ForeignKey('inventory_entries.id'), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)  # Changed to nullable=True
    old_status = db.Column(db.Enum(PaymentStatus), nullable=False)
    new_status = db.Column(db.Enum(PaymentStatus), nullable=False)
    change_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    inventory_entry = db.relationship('InventoryEntry', back_populates='payment_audits')
    supplier = db.relationship('Supplier', back_populates='payment_audits')
    user = db.relationship('User', back_populates='payment_audits')

    __table_args__ = (
        db.Index('idx_payment_audit_entry', 'inventory_entry_id'),
        db.Index('idx_payment_audit_date', 'change_date'),
    )

class SalesGrowth(db.Model):
    """Sales growth model for tracking monthly growth percentages"""
    __tablename__ = 'sales_growth'

    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)
    month = db.Column(db.Date, nullable=False)
    revenue = db.Column(db.Float, nullable=False)
    growth_percentage = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    store = db.relationship('Store', back_populates='sales_growths')
    product = db.relationship('Product', back_populates='sales_growths')

    __table_args__ = (
        db.Index('idx_sales_growth_store_month', 'store_id', 'month'),
        db.Index('idx_sales_growth_product', 'product_id'),
    )