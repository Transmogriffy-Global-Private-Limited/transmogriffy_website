from sqlalchemy import null
from tortoise import fields
from tortoise.models import Model
from Users.Data_Schemas import RoleEnum, OTPTypeEnum, AddressTypeEnum


class User(Model):
    id = fields.UUIDField(pk=True)  # Primary key field
    user_number = fields.IntField(unique=True)
    name = fields.CharField(max_length=100)
    email = fields.CharField(max_length=100, unique=True)
    email_verified = fields.BooleanField(default=False)
    phone_number = fields.BigIntField(null=True)
    password = fields.CharField(max_length=128)
    two_fa_status = fields.BooleanField(default=False)
    role = fields.CharEnumField(RoleEnum, default=RoleEnum.user)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    profile_picture = fields.BinaryField(null=True)

    class Meta:
        table = "User"


class Address(Model):
    id = fields.UUIDField(pk=True)
    user = fields.ForeignKeyField(
        "models.User", related_name="addresses", on_delete=fields.CASCADE
    )
    type = fields.CharEnumField(
        AddressTypeEnum, description="Type of Address (Home, Work, Other)"
    )
    custom_type_name = fields.CharField(
        max_length=100, null=True, description="Custom name if type is 'Other'"
    )
    house_building = fields.CharField(
        max_length=255, description="House/Building Number or Name"
    )
    locality_street = fields.CharField(
        max_length=255, description="Locality or Street Name"
    )
    landmark = fields.CharField(
        max_length=255, null=True, description="Landmark"
    )
    city = fields.CharField(max_length=100, description="City Name")
    po_ps = fields.CharField(
        max_length=100, description="Post Office or Police Station"
    )
    district = fields.CharField(max_length=100, description="District Name")
    state = fields.CharField(max_length=100, description="State Name")
    pin = fields.CharField(max_length=6, description="PIN Code")
    country = fields.CharField(max_length=100, description="Country Name")
    is_default = fields.BooleanField(
        default=True, description="Is this the default address?"
    )

    class Meta:
        table = "address"


class Blacklisted_Tokens(Model):
    Blacklisted_Tokens = fields.CharField(pk=True, max_length=512)

    class Meta:
        table = "Blacklisted_Tokens"


class OTP(Model):
    otp_code = fields.CharField(
        max_length=8, pk=True
    )  # Primary key for uniqueness
    user = fields.ForeignKeyField(
        "models.User", related_name="otps", on_delete="CASCADE"
    )
    purpose = fields.CharEnumField(
        OTPTypeEnum, description="Purpose of the OTP"
    )
    expiration = fields.DatetimeField()
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "otp"


class AdminOTP(Model):
    otp_code = fields.CharField(
        max_length=8, pk=True
    )  # Primary key for uniqueness
    admin = fields.ForeignKeyField(
        "models.Admin", related_name="otps", on_delete="CASCADE"
    )
    purpose = fields.CharEnumField(
        OTPTypeEnum, description="Purpose of the OTP"
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
    requesting_ip = fields.CharField(
        max_length=45
    )  # Supports both IPv4 and IPv6
    request = fields.JSONField()  # Stores request data in JSON format
    response = fields.JSONField(
        null=True
    )  # Stores response data in JSON format, can be null if there's an error
    endpoint_hit = fields.CharField(
        max_length=255
    )  # The endpoint that was accessed
    time_taken = (
        fields.FloatField()
    )  # Time taken to process the request, in seconds
    time_requested = fields.DatetimeField(
        auto_now_add=True
    )  # Time the request was received
    time_responded = fields.DatetimeField(
        null=True
    )  # Time the response was sent, can be null if an error occurs
    error = fields.TextField(null=True)  # Error message, if any
    error_location = fields.CharField(
        max_length=255, null=True
    )  # Location of the error, e.g., filename and line number

    class Meta:
        table = "api_activity_log"
        ordering = ["-time_requested"]


class Admin(Model):
    id = fields.UUIDField(pk=True, max_length=6)
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
        max_length=255, description="Hashed password for admin login"
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


class Product(Model):
    id = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=255)
    model = fields.CharField(max_length=255)
    details = fields.JSONField(default=dict)  # Add default empty dict
    quantity = fields.IntField(default=1)
    is_listed = fields.BooleanField(default=True)
    price = fields.FloatField(default=0.0)  # Add default value
    images = fields.JSONField(default=list)
    
    class Meta:
        table = "product"


class ProductInstance(Model):
    id = fields.UUIDField(pk=True)
    product = fields.ForeignKeyField(
        "models.Product", related_name="instances", on_delete=fields.CASCADE
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


class Cart(Model):
    id = fields.UUIDField(pk=True)
    userid = fields.CharField(default=None, max_length=600)
    productid = fields.CharField(default=None, max_length=600)
    quantity = fields.IntField(default=None,max_length=600)
    price = fields.FloatField(default=None, max_length=600)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "cart"

class Order(Model):
    id = fields.UUIDField(pk=True)
    userid = fields.CharField(default=None, max_length=600)
    productid = fields.CharField(default=None, max_length=600)
    totalamount = fields.CharField(default=None, max_length=600)
    paymentoption = fields.CharField(default=None, max_length=600)
    orderstatus = fields.CharField(default=None, max_length=600)
    ordered_quantity = fields.CharField(default=None, max_length=600)
    deliveryaddress = fields.CharField(default=None,max_length=600)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)


class Payments(Model):
    id = fields.UUIDField(pk=True)
    userid = fields.CharField(default=None, max_length=600)
    productid = fields.CharField(default=None, max_length=600)
    paymentid = fields.CharField(default=None, max_length=600)
    price = fields.FloatField(default=None, max_length=600)
    currency = fields.CharField(default=None, max_length=600)
    receipt = fields.CharField(default=None, max_length=600)
    notes = fields.CharField(default=None, max_length=600)
    paymentstatus = fields.CharField(default=None, max_length=600)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)


class Transactions(Model):
    id = fields.UUIDField(pk=True)
    razorpaypaymentid = fields.CharField(default=None, max_length=600)
    userid = fields.CharField(default=None, max_length=600)
    productid = fields.CharField(default=None, max_length=600)
    price = fields.CharField(default=None, max_length=655)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

class ContactUs(Model):
    id = fields.UUIDField(pk=True)
    firstname = fields.CharField(default=None, max_length=1200)
    lastname = fields.CharField(default=None, max_length=1200)
    telephone = fields.CharField(default=None, max_length=1200)
    email = fields.CharField(default=None,max_length=1200)
    message = fields.TextField(default=None)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)