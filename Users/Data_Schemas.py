from pydantic import BaseModel, EmailStr, Field
from enum import Enum
from typing import Optional


class RoleEnum(str, Enum):
    user = "user"
    admin = "admin"


class OTPTypeEnum(str, Enum):
    TWO_FA = "2FA"
    PASSWORD_RESET = "Password Reset"
    MAIL_VERIFICATION = "Mail Verification"
    PHONE_VERIFICATION = "Phone Number Verification"


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone_number: int


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone_number: Optional[int] = None


class LoginData(BaseModel):
    email: str
    password: str


class Toggle2FARequest(BaseModel):
    entered_password: str


class TwoFARequest(BaseModel):
    email: EmailStr
    otp_code: str


class OTPRequest(BaseModel):
    email: EmailStr
    purpose: OTPTypeEnum


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    email: EmailStr
    new_password: str
    otp_code: str


class AddressTypeEnum(str, Enum):
    Home = "Home"
    Work = "Work"
    Other = "Other"


class AddressCreate(BaseModel):
    """
    Schema for creating a new address.
    """

    type: AddressTypeEnum = Field(
        ..., description="Type of Address (Home, Work, Other)"
    )
    custom_type_name: Optional[str] = Field(
        None, description="Custom name if type is 'Other'"
    )
    house_building: str = Field(
        ..., max_length=255, description="House/Building Number or Name"
    )
    locality_street: str = Field(
        ..., max_length=255, description="Locality or Street Name"
    )
    landmark: Optional[str] = Field(
        None, max_length=255, description="Landmark (Optional)"
    )
    city: str = Field(..., max_length=100, description="City Name")
    po_ps: str = Field(
        ..., max_length=100, description="Post Office or Police Station"
    )
    district: str = Field(..., max_length=100, description="District Name")
    state: str = Field(..., max_length=100, description="State Name")
    country: str = Field(..., max_length=100, description="Country Name")
    is_default: Optional[bool] = Field(
        False, description="Is this the default address?"
    )


class AddressUpdate(BaseModel):
    """
    Schema for updating an existing address.
    """

    house_building: Optional[str] = Field(
        None, max_length=255, description="House/Building Number or Name"
    )
    locality_street: Optional[str] = Field(
        None, max_length=255, description="Locality or Street Name"
    )
    landmark: Optional[str] = Field(
        None, max_length=255, description="Landmark (Optional)"
    )
    city: Optional[str] = Field(None, max_length=100, description="City Name")
    po_ps: Optional[str] = Field(
        None, max_length=100, description="Post Office or Police Station"
    )
    district: Optional[str] = Field(
        None, max_length=100, description="District Name"
    )
    state: Optional[str] = Field(
        None, max_length=100, description="State Name"
    )
    country: Optional[str] = Field(
        None, max_length=100, description="Country Name"
    )
    is_default: Optional[bool] = Field(
        None, description="Set as the default address (Optional)"
    )
