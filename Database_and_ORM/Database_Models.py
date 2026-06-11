from enum import Enum

from tortoise import fields
from tortoise.models import Model

from Users.Data_Schemas import AddressTypeEnum, OTPTypeEnum, RoleEnum


class User(Model):
    id = fields.UUIDField(pk=True)
    user_number = fields.BigIntField(unique=True)
    name = fields.CharField(max_length=100)
    email = fields.CharField(max_length=100, unique=True)
    email_verified = fields.BooleanField(default=False)
    phone_number = fields.BigIntField(null=True)
    password = fields.CharField(max_length=128)
    two_fa_status = fields.BooleanField(default=False)
    role = fields.CharEnumField(RoleEnum, default=RoleEnum.user)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    # Preferred approach: store URL/path instead of binary blob
    profile_picture_url = fields.CharField(max_length=500, null=True)

    # Temporary legacy field kept for compatibility during migration
    profile_picture = fields.BinaryField(null=True)

    class Meta:
        table = "User"


class Address(Model):
    id = fields.UUIDField(pk=True)
    user = fields.ForeignKeyField(
        "models.User",
        related_name="addresses",
        on_delete=fields.CASCADE,
    )
    type = fields.CharEnumField(
        AddressTypeEnum,
        description="Type of Address (Home, Work, Other)",
    )
    custom_type_name = fields.CharField(
        max_length=100,
        null=True,
        description="Custom name if type is 'Other'",
    )
    house_building = fields.CharField(
        max_length=255,
        description="House/Building Number or Name",
    )
    locality_street = fields.CharField(
        max_length=255,
        description="Locality or Street Name",
    )
    landmark = fields.CharField(
        max_length=255,
        null=True,
        description="Landmark",
    )
    city = fields.CharField(max_length=100, description="City Name")
    po_ps = fields.CharField(
        max_length=100,
        description="Post Office or Police Station",
    )
    district = fields.CharField(max_length=100, description="District Name")
    state = fields.CharField(max_length=100, description="State Name")
    pin = fields.CharField(max_length=6, description="PIN Code")
    country = fields.CharField(max_length=100, description="Country Name")
    is_default = fields.BooleanField(
        default=True,
        description="Is this the default address?",
    )

    class Meta:
        table = "address"


class Blacklisted_Tokens(Model):
    Blacklisted_Tokens = fields.CharField(pk=True, max_length=512)

    class Meta:
        table = "Blacklisted_Tokens"


class OTP(Model):
    otp_code = fields.CharField(max_length=8, pk=True)
    user = fields.ForeignKeyField(
        "models.User",
        related_name="otps",
        on_delete=fields.CASCADE,
    )
    purpose = fields.CharEnumField(
        OTPTypeEnum,
        description="Purpose of the OTP",
    )
    expiration = fields.DatetimeField()
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "otp"


class AdminOTP(Model):
    otp_code = fields.CharField(max_length=8, pk=True)
    admin = fields.ForeignKeyField(
        "models.Admin",
        related_name="otps",
        on_delete=fields.CASCADE,
    )
    purpose = fields.CharEnumField(
        OTPTypeEnum,
        description="Purpose of the OTP",
    )
    expiration = fields.DatetimeField()
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "admin_otp"


class APIActivityLog(Model):
    """
    Model to track API activity details such as IP address, request, response,
    endpoint, timings, and errors.
    """

    id = fields.UUIDField(pk=True)
    requesting_ip = fields.CharField(max_length=45)
    request = fields.JSONField()
    response = fields.JSONField(null=True)
    endpoint_hit = fields.CharField(max_length=255)
    time_taken = fields.FloatField()
    time_requested = fields.DatetimeField(auto_now_add=True)
    time_responded = fields.DatetimeField(null=True)
    error = fields.TextField(null=True)
    error_location = fields.CharField(max_length=255, null=True)

    class Meta:
        table = "api_activity_log"
        ordering = ["-time_requested"]


class Admin(Model):
    id = fields.UUIDField(pk=True)
    role = fields.CharEnumField(
        RoleEnum,
        max_length=5,
        default=RoleEnum.admin,
        description="Role of the admin",
    )
    name = fields.CharField(max_length=255, description="Name of the admin")
    email = fields.CharField(max_length=100, unique=True)
    email_verified = fields.BooleanField(default=False)
    password = fields.CharField(
        max_length=255,
        description="Hashed password for admin login",
    )
    two_fa_status = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(
        auto_now_add=True,
        description="Timestamp when the admin was created",
    )
    updated_at = fields.DatetimeField(
        auto_now=True,
        description="Timestamp when the admin was last updated",
    )

    class Meta:
        table = "admin"
        ordering = ["created_at"]


# ========== ENUMS ==========

class OrderStatusEnum(str, Enum):
    PAYMENT_PENDING = "payment_pending"
    PAID = "paid"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUND_PENDING = "refund_pending"
    REFUNDED = "refunded"


class PaymentStatusEnum(str, Enum):
    CREATED = "created"
    VERIFIED = "verified"
    FAILED = "failed"
    REFUNDED = "refunded"


class OrderPaymentStatusEnum(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUND_PENDING = "refund_pending"
    REFUNDED = "refunded"


class RefundStatusEnum(str, Enum):
    CREATED = "created"
    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"


# ========== PRODUCT / CART / REVIEW ==========

class Product(Model):
    id = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=255)
    model = fields.CharField(max_length=255)
    details = fields.JSONField(default=dict)
    quantity = fields.IntField(default=1)
    product_color = fields.CharField(max_length=255)
    is_listed = fields.BooleanField(default=True)

    # Temporary legacy fields for safe migration
    price = fields.FloatField(default=0.0)
    mrp = fields.FloatField(default=0.0)

    # New money fields
    price_paise = fields.IntField(null=True)
    mrp_paise = fields.IntField(null=True)
    currency = fields.CharField(max_length=10, default="INR")

    images = fields.JSONField(default=list)

    class Meta:
        table = "product"


class Cart(Model):
    id = fields.UUIDField(pk=True)

    user = fields.ForeignKeyField(
        "models.User",
        related_name="cart_items",
        on_delete=fields.CASCADE,
    )

    product = fields.ForeignKeyField(
        "models.Product",
        related_name="cart_items",
        on_delete=fields.CASCADE,
    )

    quantity = fields.IntField(default=1)
    unit_price_paise = fields.IntField()
    added_at = fields.DatetimeField(auto_now_add=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "cart"
        unique_together = (("user", "product"),)


class ProductReview(Model):
    id = fields.UUIDField(pk=True)

    product = fields.ForeignKeyField(
        "models.Product",
        related_name="reviews",
        on_delete=fields.CASCADE,
    )
    user = fields.ForeignKeyField(
        "models.User",
        related_name="product_reviews",
        on_delete=fields.CASCADE,
    )

    rating = fields.IntField(description="Rating from 1 to 5")
    review = fields.TextField(null=True)
    is_visible = fields.BooleanField(default=True)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    def _validate_rating(self):
        if not 1 <= self.rating <= 5:
            raise ValueError("rating must be between 1 and 5")

    async def save(self, *args, **kwargs):
        self._validate_rating()
        await super().save(*args, **kwargs)

    class Meta:
        table = "product_review"
        unique_together = (("product", "user"),)
        indexes = (
            ("product", "is_visible"),
            ("user",),
        )


class ProductInstance(Model):
    id = fields.UUIDField(pk=True)
    product = fields.ForeignKeyField(
        "models.Product",
        related_name="instances",
        on_delete=fields.CASCADE,
    )
    serial_number = fields.CharField(
        max_length=255,
        unique=True,
        description="Unique Serial Number of the Product Instance",
    )

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "product_instance"


# ========== NEW V2 MODELS ==========

class OrderV2(Model):
    id = fields.UUIDField(pk=True)
    user = fields.ForeignKeyField(
        "models.User",
        related_name="orders",
    )
    address = fields.ForeignKeyField(
        "models.Address",
        related_name="orders",
    )
    status = fields.CharEnumField(
        OrderStatusEnum,
        default=OrderStatusEnum.PAYMENT_PENDING,
    )
    payment_status = fields.CharEnumField(
        OrderPaymentStatusEnum,
        default=OrderPaymentStatusEnum.PENDING,
    )
    subtotal_paise = fields.IntField()
    total_paise = fields.IntField()
    currency = fields.CharField(max_length=10, default="INR")
    checkout_hash = fields.CharField(max_length=255, null=True, unique=True)
    razorpay_order_id = fields.CharField(
        max_length=255,
        null=True,
        unique=True,
    )
    razorpay_payment_id = fields.CharField(
        max_length=255,
        null=True,
        unique=True,
    )
    paid_at = fields.DatetimeField(null=True)
    cancelled_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "orders_v2"
        indexes = (
            ("user",),
            ("status",),
            ("razorpay_order_id",),
            ("razorpay_payment_id",),
        )


class OrderItem(Model):
    id = fields.UUIDField(pk=True)
    order = fields.ForeignKeyField(
        "models.OrderV2",
        related_name="items",
    )
    product = fields.ForeignKeyField(
        "models.Product",
        null=True,
        on_delete=fields.SET_NULL,
    )
    product_name_snapshot = fields.CharField(max_length=255)
    product_model_snapshot = fields.CharField(max_length=255)
    product_details_snapshot = fields.JSONField(null=True)
    currency = fields.CharField(max_length=10, default="INR")
    unit_price_paise = fields.IntField()
    quantity = fields.IntField()
    line_total_paise = fields.IntField()

    class Meta:
        table = "order_items"


class PaymentsV2(Model):
    id = fields.UUIDField(pk=True)
    order = fields.OneToOneField(
        "models.OrderV2",
        related_name="payment",
        on_delete=fields.CASCADE,
    )
    provider = fields.CharField(
        max_length=50,
        default="razorpay",
    )
    razorpay_order_id = fields.CharField(max_length=255)
    razorpay_payment_id = fields.CharField(
        max_length=255,
        unique=True,
        null=True,
    )
    razorpay_signature = fields.TextField(null=True)
    amount_paise = fields.IntField()
    currency = fields.CharField(max_length=10)
    status = fields.CharEnumField(
        PaymentStatusEnum,
        default=PaymentStatusEnum.CREATED,
    )
    raw_payload = fields.JSONField(null=True)
    provider_response = fields.JSONField(null=True)
    verified_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "payments_v2"
        indexes = (
            ("razorpay_order_id",),
            ("razorpay_payment_id",),
            ("status",),
        )


class RefundV2(Model):
    id = fields.UUIDField(pk=True)
    order = fields.ForeignKeyField(
        "models.OrderV2",
        related_name="refunds",
        on_delete=fields.CASCADE,
    )
    payment = fields.ForeignKeyField(
        "models.PaymentsV2",
        related_name="refunds",
        on_delete=fields.CASCADE,
    )
    razorpay_refund_id = fields.CharField(
        max_length=255,
        unique=True,
        null=True,
    )
    amount_paise = fields.IntField()
    processed_amount_paise = fields.IntField(default=0)
    reason = fields.TextField(null=True)
    status = fields.CharEnumField(RefundStatusEnum)
    raw_payload = fields.JSONField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "refunds_v2"
        indexes = (
            ("order",),
            ("payment",),
            ("status",),
        )


class InventoryReservation(Model):
    id = fields.UUIDField(pk=True)

    user = fields.ForeignKeyField("models.User")
    product = fields.ForeignKeyField("models.Product")

    quantity = fields.IntField()
    expires_at = fields.DatetimeField()
    converted = fields.BooleanField(default=False)
    released = fields.BooleanField(default=False)
    released_at = fields.DatetimeField(null=True)
    expired = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "inventory_reservation"
        indexes = (
            ("product",),
            ("user",),
            ("expires_at",),
            ("converted",),
            ("released",),
        )


class WebhookEvent(Model):
    id = fields.UUIDField(pk=True)
    provider = fields.CharField(max_length=50)
    event_id = fields.CharField(max_length=255, unique=True)
    event_type = fields.CharField(max_length=255)
    payload = fields.JSONField()
    processed = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "webhook_events"


# ========== TEMPORARY LEGACY MODELS (READ-ONLY COMPATIBILITY) ==========
# Recommendation:
# - Keep these models only for backward compatibility / old reads
# - Route all new writes to V2 models only


class Order(Model):
    id = fields.UUIDField(pk=True)
    userid = fields.CharField(default=None, max_length=600, null=True)
    productid = fields.CharField(default=None, max_length=600, null=True)
    totalamount = fields.CharField(default=None, max_length=600, null=True)
    paymentoption = fields.CharField(default=None, max_length=600, null=True)
    rzp_payment_id = fields.CharField(default="default_id", max_length=600)
    rzp_order_id = fields.CharField(default="default_id", max_length=600)
    orderstatus = fields.CharField(default=None, max_length=600, null=True)
    ordered_quantity = fields.CharField(default=None, max_length=600, null=True)
    deliveryaddress = fields.CharField(default=None, max_length=600, null=True)
    reasonforcancel = fields.CharField(default=None, max_length=600, null=True)
    otherreasonforcancel = fields.CharField(default=None, max_length=600, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "order"


class Payments(Model):
    id = fields.UUIDField(pk=True)
    userid = fields.CharField(default=None, max_length=600, null=True)
    productid = fields.CharField(default=None, max_length=600, null=True)
    paymentid = fields.CharField(default=None, max_length=600, null=True)
    price = fields.FloatField(default=None, null=True)
    currency = fields.CharField(default=None, max_length=600, null=True)
    receipt = fields.CharField(default=None, max_length=600, null=True)
    notes = fields.CharField(default=None, max_length=600, null=True)
    paymentstatus = fields.CharField(default=None, max_length=600, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "payments"


class Transactions(Model):
    id = fields.UUIDField(pk=True)
    razorpaypaymentid = fields.CharField(default=None, max_length=600, null=True)
    userid = fields.CharField(default=None, max_length=600, null=True)
    productid = fields.CharField(default=None, max_length=600, null=True)
    price = fields.CharField(default=None, max_length=655, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "transactions"


class BuyNow(Model):
    id = fields.UUIDField(pk=True)
    user_id = fields.CharField(max_length=600, description="ID of the user")
    product_id = fields.CharField(max_length=600, description="ID of the product")
    address_id = fields.CharField(max_length=600, description="ID of the delivery address")
    quantity = fields.IntField(default=1, description="Quantity of the product")
    price = fields.IntField(description="Total price for the purchase in paise")
    currency = fields.CharField(max_length=10, default="INR")
    payment_method = fields.CharField(max_length=100, description="Payment method used")
    order_status = fields.CharField(max_length=100, description="Current status of the order")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "buynow"


class ContactUs(Model):
    id = fields.UUIDField(pk=True)
    firstname = fields.CharField(default=None, max_length=1200, null=True)
    lastname = fields.CharField(default=None, max_length=1200, null=True)
    telephone = fields.CharField(default=None, max_length=1200, null=True)
    email = fields.CharField(default=None, max_length=1200, null=True)
    message = fields.TextField(default=None, null=True)
    contacted_at = fields.DatetimeField(null=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "contact_us"


class ClickEvent(Model):
    id = fields.UUIDField(pk=True)
    user_id = fields.CharField(max_length=100, null=True)
    session_id = fields.CharField(max_length=100, null=True)
    page_url = fields.TextField()
    element_id = fields.CharField(max_length=255, null=True)
    element_class = fields.CharField(max_length=255, null=True)
    element_text = fields.TextField(null=True)
    click_x = fields.IntField(null=True)
    click_y = fields.IntField(null=True)
    referrer = fields.TextField(null=True)
    user_agent = fields.TextField(null=True)
    ip_address = fields.CharField(max_length=45, null=True)
    timestamp = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "click_events"

    def __str__(self):
        return f"ClickEvent(user={self.user_id}, element={self.element_id}, page={self.page_url})"


class Refund_Instances(Model):
    id = fields.UUIDField(pk=True)
    rzp_payment_id = fields.CharField(max_length=600)
    rzp_refund_id = fields.CharField(
        max_length=600,
        null=True,
        unique=True,
    )
    order_id = fields.CharField(max_length=600)
    total_order_amount_paise = fields.IntField()
    refund_amount_paise = fields.IntField()
    refund_status = fields.CharEnumField(
        RefundStatusEnum,
        default=RefundStatusEnum.CREATED,
        max_length=20,
    )
    failure_reason = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "refund_instances"
        ordering = ["-created_at"]