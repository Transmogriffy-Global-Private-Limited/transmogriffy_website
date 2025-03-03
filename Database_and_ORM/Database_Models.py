from tortoise import fields
from tortoise.models import Model
from Users.Data_Schemas import RoleEnum, OTPTypeEnum, AddressTypeEnum


class User(Model):
    id = fields.UUIDField(pk=True)  # Primary key field
    name = fields.CharField(max_length=100)
    email = fields.CharField(max_length=100, unique=True)
    email_verified = fields.BooleanField(default=False)
    phone_number = fields.BigIntField(null=True)
    password = fields.CharField(max_length=128)
    two_fa_status = fields.BooleanField(default=False)
    role = fields.CharEnumField(RoleEnum, default=RoleEnum.user)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    profile_picture_path = fields.CharField(max_length=255, null=True)

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
    country = fields.CharField(max_length=100, description="Country Name")
    is_default = fields.BooleanField(
        default=True, description="Is this the default address?"
    )

    class Meta:
        table = "address"


class Blacklisted_Tokens(Model):
    Blacklisted_Tokens = fields.CharField(pk=True, max_length=2048)

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
