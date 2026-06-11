#payments/Data_Schemas.py
from tortoise import fields
from enum import Enum
from pydantic import BaseModel, UUID4, Field
from typing import List, Optional


class ProductItemSchema(BaseModel):
    productid: str
    quantity: int

class PaymentSchema(BaseModel):
    user_id: str
    products: List[ProductItemSchema]
    price: Optional[float] = None

class TransactionProductSchema(BaseModel):
    productid: str
    price: float

class VerifyPaymentSchema(BaseModel):
    order_id: str
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
class TransactionsHistoryUser(BaseModel):
    user_id: Optional[str] = None
