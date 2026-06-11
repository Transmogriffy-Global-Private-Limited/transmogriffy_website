from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, UUID4, Field
from tortoise import fields

# -----------------------------------------------------------------------------
# Nested Product Schema
# -----------------------------------------------------------------------------
class ProductItemSchema(BaseModel):
    productid: str
    quantity: int

# -----------------------------------------------------------------------------
# Payment & Checkout Schemas
# -----------------------------------------------------------------------------
class PaymentSchema(BaseModel):
    user_id: str
    order_id: str  # Tightly binds your internal DB order record to the payload
    products: List[ProductItemSchema]
    price: Optional[float] = None

class TransactionProductSchema(BaseModel):
    productid: str
    price: float

# -----------------------------------------------------------------------------
# Verification & History Schemas
# -----------------------------------------------------------------------------
class VerifyPaymentSchema(BaseModel):
    order_id: str             # Internal System UUID string
    razorpay_order_id: str    # Razorpay Order reference string (order_...)
    razorpay_payment_id: str  # Razorpay Payment identification string (pay_...)
    razorpay_signature: str   # Cryptographic webhook signature verify string

class TransactionsHistoryUser(BaseModel):
    user_id: Optional[str] = None