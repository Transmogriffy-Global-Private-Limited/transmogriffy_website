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

class TransactionsSchema(BaseModel):
    user_id: str
    razorpaypaymentid: str
    products: List[TransactionProductSchema]
class TransactionsHistoryUser(BaseModel):
    user_id: Optional[str] = None
