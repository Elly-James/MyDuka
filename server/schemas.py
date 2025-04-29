# schemas.py
from marshmallow import Schema, fields, validate, ValidationError
from models import UserRole, PaymentStatus, RequestStatus, UserStatus

class UserSchema(Schema):
    email = fields.Email(required=True)
    name = fields.Str(required=True, validate=validate.Length(min=2))
    role = fields.Str(required=True, validate=validate.OneOf([r.name for r in UserRole]))  # MERCHANT, ADMIN, CLERK
    status = fields.Str(validate=validate.OneOf([s.value for s in UserStatus]))  # Use values: active, inactive

class ProductSchema(Schema):
    name = fields.Str(required=True)
    sku = fields.Str()
    category_id = fields.Int()
    store_id = fields.Int(required=True)
    min_stock_level = fields.Int(validate=validate.Range(min=0))
    current_stock = fields.Int(validate=validate.Range(min=0))

class InventoryEntrySchema(Schema):
    product_id = fields.Int(required=True)
    quantity_received = fields.Int(required=True, validate=validate.Range(min=1))
    quantity_spoiled = fields.Int(validate=validate.Range(min=0))
    buying_price = fields.Float(required=True, validate=validate.Range(min=0.01))
    selling_price = fields.Float(required=True, validate=validate.Range(min=0.01))
    payment_status = fields.Str(validate=validate.OneOf([s.value for s in PaymentStatus]))
    supplier_id = fields.Int()

class SupplyRequestSchema(Schema):
    product_id = fields.Int(required=True)
    quantity_requested = fields.Int(required=True, validate=validate.Range(min=1))
    status = fields.Str(validate=validate.OneOf([s.value for s in RequestStatus]))

class NotificationSchema(Schema):
    id = fields.Int(dump_only=True)
    user_id = fields.Int(required=True)
    message = fields.Str(required=True, validate=validate.Length(min=1, max=500))
    is_read = fields.Boolean(default=False)
    created_at = fields.DateTime(dump_only=True)

class InvitationSchema(Schema):
    id = fields.Int(dump_only=True)
    email = fields.Email(required=True)
    token = fields.Str(dump_only=True)
    role = fields.Str(required=True, validate=validate.OneOf([r.name for r in UserRole]))
    creator_id = fields.Int(required=True)
    store_id = fields.Int(allow_none=True)
    is_used = fields.Boolean(default=False)
    expires_at = fields.DateTime(required=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

class PasswordResetSchema(Schema):
    id = fields.Int(dump_only=True)
    user_id = fields.Int(required=True)
    token = fields.Str(dump_only=True)
    is_used = fields.Boolean(default=False)
    expires_at = fields.DateTime(required=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

class ChartDatasetSchema(Schema):
    label = fields.Str(required=True)
    data = fields.List(fields.Float(), required=True)
    backgroundColor = fields.Str(missing='#2E3A8C')

class ChartDataSchema(Schema):
    labels = fields.List(fields.Str(), required=True)
    datasets = fields.List(fields.Nested(ChartDatasetSchema), required=True)

class SalesReportSchema(Schema):
    total_quantity_sold = fields.Int(required=True)
    total_revenue = fields.Float(required=True)
    chart_data = fields.Nested(ChartDataSchema, required=True)

class SpoilageReportSchema(Schema):
    total_spoilage = fields.Int(required=True)
    chart_data = fields.Nested(ChartDataSchema, required=True)

class PaymentStatusReportSchema(Schema):
    total_paid = fields.Float(required=True)
    total_unpaid = fields.Float(required=True)
    chart_data = fields.Nested(ChartDataSchema, required=True)

class StoreComparisonReportSchema(Schema):
    chart_data = fields.Nested(ChartDataSchema, required=True)

class ClerkPerformanceReportSchema(Schema):
    clerk_id = fields.Int(required=True)
    clerk_name = fields.Str(required=True)
    total_entries = fields.Int(required=True)
    total_received = fields.Int(required=True)
    total_spoiled = fields.Int(required=True)
    total_sales = fields.Float(required=True)

class SalesChartDataSchema(Schema):
    weekly = fields.Nested(ChartDataSchema, required=True)
    monthly = fields.Nested(ChartDataSchema, required=True)
    annual = fields.Nested(ChartDataSchema, required=True)

class UserStatusUpdateSchema(Schema):
    id = fields.Int(required=True)
    status = fields.Str(required=True, validate=validate.OneOf([s.value for s in UserStatus]))  # Use values: active, inactive

class UserStatusInputSchema(Schema):
    status = fields.Str(required=True, validate=validate.OneOf([s.value for s in UserStatus]))  # Use values: active, inactive