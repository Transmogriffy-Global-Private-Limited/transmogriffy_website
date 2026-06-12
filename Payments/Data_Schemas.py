from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, UUID4, Field

# -----------------------------------------------------------------------------
# SUB-SCHEMA DEFINITION FOR INDIVIDUAL BASKET ITEMS
# -----------------------------------------------------------------------------
class ProductItemSchema(BaseModel):
    productid: str
    quantity: int


class TransactionProductSchema(BaseModel):
    productid: str
    price: float


# -----------------------------------------------------------------------------
# CORE TRANSACTION Captured DATA LAYER SCHEMAS
# -----------------------------------------------------------------------------
class PaymentSchema(BaseModel):
    user_id: str
    products: List[ProductItemSchema]
    price: Optional[float] = None


class VerifyPaymentSchema(BaseModel):
    razorpay_order_id: str = Field(..., description="The payment staging token target reference string")
    razorpay_payment_id: str = Field(..., description="The finalized captured payment ID identifier token")
    razorpay_signature: str = Field(..., description="The cryptographic payload authenticity verification signature hash")


class TransactionsSchema(BaseModel):
    user_id: str
    razorpaypaymentid: str
    products: List[TransactionProductSchema]

    class Config:
        from_attributes = True


class TransactionsHistoryUser(BaseModel):
    user_id: Optional[str] = None