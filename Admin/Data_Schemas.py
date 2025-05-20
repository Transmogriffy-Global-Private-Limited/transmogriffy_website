from pydantic import BaseModel, EmailStr, Field
from enum import Enum
from typing import Optional


class AdminCreate(BaseModel):
    name: str
    email: EmailStr
    password: str


class RoleEnum(str, Enum):
    user = "user"
    admin = "admin"


class OTPTypeEnum(str, Enum):
    TWO_FA = "2FA"
    PASSWORD_RESET = "Password Reset"
    MAIL_VERIFICATION = "Mail Verification"
    PHONE_VERIFICATION = "Phone Number Verification"


class AdminUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    password: str


class LoginData(BaseModel):
    email: str
    password: str


class Toggle2FARequest(BaseModel):
    entered_password: str


class TwoFARequest(BaseModel):
    email: EmailStr
    otp_code: str


class OTPRequest(BaseModel):
    email: Optional[EmailStr]= None
    purpose: OTPTypeEnum
    id: Optional[str] = None
    otp_code: Optional[str]=None


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    email: EmailStr
    new_password: str
    otp_code: str


class ViewUsersRequest(BaseModel):
    user_id: Optional[str] = Field(
        None, description="The ID of the user to retrieve"
    )
    limit: Optional[str] = Field(
        None,
        pattern=r"^\d+-\d+$",
        description="Pagination range in 'start-end' format",
    )
