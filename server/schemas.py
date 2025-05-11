from datetime import timedelta
from marshmallow import Schema, fields, validate, ValidationError, post_dump
from models import UserRole, PaymentStatus, RequestStatus, UserStatus, InvitationStatus, NotificationType

class StoreSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    address = fields.Str(allow_none=True)
    location = fields.Str(allow_none=True)
    description = fields.Str(allow_none=True)
    users = fields.List(fields.Nested(lambda: UserSchema(only=('id', 'name', 'email', 'role'))))
    products = fields.List(fields.Nested(lambda: ProductSchema(only=('id', 'name', 'sku', 'unit_price'))))
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

class UserSchema(Schema):
    id = fields.Int(dump_only=True)
    email = fields.Email(required=True)
    name = fields.Str(required=True, validate=validate.Length(min=2))
    role = fields.Method("get_role", dump_only=True)
    status = fields.Method("get_status", dump_only=True)
    stores = fields.List(fields.Nested(StoreSchema(only=('id', 'name'))), dump_only=True)
    store = fields.Dict(allow_none=True, dump_only=True)  # For single store in login/register responses
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    def get_role(self, obj):
        return obj.role.name if obj.role else None

    def get_status(self, obj):
        return obj.status.name if obj.status else None

    @post_dump
    def limit_stores(self, data, **kwargs):
        # Limit to one store for display purposes
        if data.get('stores') and len(data['stores']) > 0:
            data['stores'] = [data['stores'][0]]
        return data

class ProductSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    sku = fields.Str(allow_none=True)
    category_id = fields.Int(allow_none=True)
    store_id = fields.Int(required=True)
    min_stock_level = fields.Int(validate=validate.Range(min=0))
    current_stock = fields.Int(validate=validate.Range(min=0))
    unit_price = fields.Float(required=True, validate=validate.Range(min=0.01))
    buying_price = fields.Float(allow_none=True, validate=validate.Range(min=0.01))
    is_low_stock = fields.Boolean(dump_only=True)
    category = fields.Nested(lambda: ProductCategorySchema(only=('id', 'name')))
    store = fields.Nested(StoreSchema(only=('id', 'name')))
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

class ProductCategorySchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    description = fields.Str(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

class SupplierSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    email = fields.Email(allow_none=True)
    phone = fields.Str(allow_none=True)
    address = fields.Str(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

class InventoryEntrySchema(Schema):
    id = fields.Int(dump_only=True)
    product_id = fields.Int(required=True)
    product = fields.Nested(ProductSchema(only=('id', 'name', 'sku', 'unit_price', 'buying_price')))
    store_id = fields.Int(required=True)
    store = fields.Nested(StoreSchema(only=('id', 'name')))
    category_id = fields.Int(allow_none=True)
    category = fields.Nested(ProductCategorySchema(only=('id', 'name')))
    quantity_received = fields.Int(required=True, validate=validate.Range(min=1))
    quantity_spoiled = fields.Int(default=0, validate=validate.Range(min=0))  # Renamed to match inventory.py
    buying_price = fields.Float(required=True, validate=validate.Range(min=0.01))
    selling_price = fields.Float(required=True, validate=validate.Range(min=0.01))
    payment_status = fields.Str(required=True, validate=validate.OneOf([status.name for status in PaymentStatus]))
    payment_date = fields.DateTime(allow_none=True)
    supplier_id = fields.Int(allow_none=True)
    supplier = fields.Nested(SupplierSchema(only=('id', 'name')))
    recorded_by = fields.Int(required=True)
    clerk = fields.Nested(UserSchema(only=('id', 'name')))
    due_date = fields.DateTime(allow_none=True)
    entry_date = fields.DateTime(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    spoilage_value = fields.Float(dump_only=True)

class SalesRecordSchema(Schema):
    id = fields.Int(dump_only=True)
    product_id = fields.Int(required=True)
    product = fields.Nested(ProductSchema(only=('id', 'name', 'sku', 'unit_price')))
    store_id = fields.Int(required=True)
    store = fields.Nested(StoreSchema(only=('id', 'name')))
    quantity_sold = fields.Int(required=True, validate=validate.Range(min=1))
    selling_price = fields.Float(required=True, validate=validate.Range(min=0.01))
    revenue = fields.Float(dump_only=True)
    sale_date = fields.DateTime(required=True)
    recorded_by_id = fields.Int(required=True)
    recorded_by = fields.Nested(UserSchema(only=('id', 'name')))
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

class SupplyRequestSchema(Schema):
    id = fields.Int(dump_only=True)
    product_id = fields.Int(required=True)
    product = fields.Nested(ProductSchema(only=('id', 'name', 'sku')))
    store_id = fields.Int(required=True)
    store = fields.Nested(StoreSchema(only=('id', 'name')))
    quantity_requested = fields.Int(required=True, validate=validate.Range(min=1))
    clerk_id = fields.Int(required=True)
    clerk = fields.Nested(UserSchema(only=('id', 'name')))
    admin_id = fields.Int(allow_none=True)
    admin = fields.Nested(UserSchema(only=('id', 'name')))
    status = fields.Str(required=True, validate=validate.OneOf([status.name for status in RequestStatus]))
    decline_reason = fields.Str(allow_none=True)
    approval_date = fields.DateTime(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

class NotificationSchema(Schema):
    id = fields.Int(dump_only=True)
    user_id = fields.Int(allow_none=True)
    user = fields.Nested(UserSchema(only=('id', 'name')))
    message = fields.Str(required=True, validate=validate.Length(min=1, max=500))
    type = fields.Str(required=True, validate=validate.OneOf([ntype.name for ntype in NotificationType]))
    related_entity_id = fields.Int(allow_none=True)
    related_entity_type = fields.Str(allow_none=True)
    is_read = fields.Boolean(default=False)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

class InvitationSchema(Schema):
    id = fields.Int(dump_only=True)
    email = fields.Email(required=True)
    token = fields.Str(dump_only=True)
    role = fields.Method("get_role", dump_only=True)
    creator_id = fields.Int(required=True)
    creator = fields.Nested(UserSchema(only=('id', 'name')))
    store_id = fields.Int(required=True)
    store = fields.Nested(StoreSchema(only=('id', 'name')))
    status = fields.Str(required=True, validate=validate.OneOf([status.name for status in InvitationStatus]))
    is_used = fields.Boolean(default=False)
    expires_at = fields.DateTime(required=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    def get_role(self, obj):
        return obj.role.name if obj.role else None

class PasswordResetSchema(Schema):
    id = fields.Int(dump_only=True)
    user_id = fields.Int(required=True)
    user = fields.Nested(UserSchema(only=('id', 'name')))
    token = fields.Str(dump_only=True)
    is_used = fields.Boolean(default=False)
    expires_at = fields.DateTime(required=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

class PaymentAuditSchema(Schema):
    id = fields.Int(dump_only=True)
    inventory_entry_id = fields.Int(required=True)
    supplier_id = fields.Int(allow_none=True)
    user_id = fields.Int(required=True)
    user = fields.Nested(UserSchema(only=('id', 'name')))
    old_status = fields.Str(required=True, validate=validate.OneOf([status.name for status in PaymentStatus]))
    new_status = fields.Str(required=True, validate=validate.OneOf([status.name for status in PaymentStatus]))
    change_date = fields.DateTime(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

class SalesGrowthSchema(Schema):
    id = fields.Int(dump_only=True)
    store_id = fields.Int(required=True)
    store = fields.Nested(StoreSchema(only=('id', 'name')))
    product_id = fields.Int(allow_none=True)
    product = fields.Nested(ProductSchema(only=('id', 'name', 'sku')))
    month = fields.Date(required=True)
    revenue = fields.Float(required=True)
    growth_percentage = fields.Float(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

class ChartDatasetSchema(Schema):
    label = fields.Str(required=True)
    data = fields.List(fields.Float(), required=True, validate=validate.Length(min=0))
    backgroundColor = fields.Raw(required=True)  # String or list of strings
    borderColor = fields.Raw(allow_none=True)  # String or list of strings
    type = fields.Str(dump_only=True)

class ChartDataSchema(Schema):
    labels = fields.List(fields.Str(), required=True, validate=validate.Length(min=0))
    datasets = fields.List(fields.Nested(ChartDatasetSchema), required=True, validate=validate.Length(min=0))

class SalesReportSchema(Schema):
    total_quantity_sold = fields.Int(required=True, validate=validate.Range(min=0))
    total_revenue = fields.Float(required=True, validate=validate.Range(min=0))
    chart_data = fields.Nested(ChartDataSchema, required=True)

class SpoilageReportSchema(Schema):
    total_spoilage_value = fields.Float(required=True, validate=validate.Range(min=0))
    chart_data = fields.Nested(ChartDataSchema, required=True)

class PaymentStatusReportSchema(Schema):
    total_paid = fields.Float(required=True, validate=validate.Range(min=0))
    total_unpaid = fields.Float(required=True, validate=validate.Range(min=0))
    suppliers = fields.List(
        fields.Dict(
            keys=fields.Str(),
            values=fields.Raw(),
            required=True,
            validate=lambda x: all(k in ['name', 'paid_amount', 'unpaid_amount'] for k in x.keys())
        ),
        required=True
    )

class TopProductSchema(Schema):
    product_name = fields.Str(required=True)
    units_sold = fields.Int(required=True, validate=validate.Range(min=0))
    revenue = fields.Float(required=True, validate=validate.Range(min=0))
    unit_price = fields.Float(required=True, validate=validate.Range(min=0))
    growth = fields.Float(required=True)

class StoreComparisonReportSchema(Schema):
    chart_data = fields.Nested(ChartDataSchema, required=True)

class ClerkPerformanceReportSchema(Schema):
    clerk_id = fields.Int(required=True)
    clerk_name = fields.Str(required=True)
    total_entries = fields.Int(required=True, validate=validate.Range(min=0))
    total_received = fields.Int(required=True, validate=validate.Range(min=0))
    total_spoilage_value = fields.Float(required=True, validate=validate.Range(min=0))
    total_sales = fields.Float(required=True, validate=validate.Range(min=0))

class DashboardSummarySchema(Schema):
    low_stock_count = fields.Int(required=True, validate=validate.Range(min=0))
    low_stock_products = fields.List(
        fields.Dict(
            keys=fields.Str(),
            values=fields.Raw(),
            required=True,
            validate=lambda x: all(k in ['name', 'current_stock', 'min_stock_level'] for k in x.keys())
        ),
        required=True
    )
    normal_stock_count = fields.Int(required=True, validate=validate.Range(min=0))
    total_sales = fields.Float(required=True, validate=validate.Range(min=0))
    total_spoilage_value = fields.Float(required=True, validate=validate.Range(min=0))
    spoilage_percentage = fields.Float(required=True, validate=validate.Range(min=0, max=100))
    unpaid_suppliers_count = fields.Int(required=True, validate=validate.Range(min=0))
    unpaid_suppliers_amount = fields.Float(required=True, validate=validate.Range(min=0))
    paid_suppliers_count = fields.Int(required=True, validate=validate.Range(min=0))
    paid_suppliers_amount = fields.Float(required=True, validate=validate.Range(min=0))
    paid_percentage = fields.Float(required=True, validate=validate.Range(min=0, max=100))
    unpaid_percentage = fields.Float(required=True, validate=validate.Range(min=0, max=100))

class StoreDetailSchema(StoreSchema):
    sales_summary = fields.Dict(dump_only=True)
    inventory_status = fields.Dict(dump_only=True)
    financial_overview = fields.Dict(dump_only=True)
    top_products = fields.List(fields.Dict(), dump_only=True)
    spoilage_summary = fields.Dict(dump_only=True)