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
    address: str
    pin_code: int
    phone_number: int


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    pin_code: Optional[int] = None
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
