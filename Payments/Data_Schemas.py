from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

# -----------------------------------------------------------------------------
# SUB-SCHEMA DEFINITION FOR INDIVIDUAL BASKET ITEMS
# -----------------------------------------------------------------------------
class ProductItemSchema(BaseModel):
    productid: str
    quantity: int
    price: Optional[float] = None


class TransactionProductSchema(BaseModel):
    productid: str
    price: float


# -----------------------------------------------------------------------------
# CORE TRANSACTION CAPTURED DATA LAYER SCHEMAS
# -----------------------------------------------------------------------------
class PaymentSchema(BaseModel):
    user_id: str
    products: List[ProductItemSchema]
    price: Optional[float] = None


class VerifyPaymentSchema(BaseModel):
    # ✅ FIXED: Configured explicit validation aliases to parse incoming frontend keys cleanly
    razorpay_payment_id: str = Field(..., validation_alias="razorpaypaymentid", description="The captured payment token reference identifier")
    user_id: str = Field(..., validation_alias="user_id", description="The core user unique identity reference anchor token")
    products: List[ProductItemSchema] = Field(..., description="The verified items manifest tracking list array")
    
    # ✅ FIXED: Configured signature and order parameters as Optional fallbacks to prevent client validation drops
    razorpay_order_id: Optional[str] = Field(None, validation_alias="razorpay_order_id")
    razorpay_signature: Optional[str] = Field(None, validation_alias="razorpay_signature")

    class Config:
        populate_by_name = True
        from_attributes = True


class TransactionsSchema(BaseModel):
    user_id: str
    razorpaypaymentid: str
    products: List[TransactionProductSchema]

    class Config:
        from_attributes = True


class TransactionsHistoryUser(BaseModel):
    user_id: Optional[str] = None