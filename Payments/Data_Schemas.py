from tortoise import fields
from enum import Enum
from pydantic import BaseModel, UUID4, Field
from typing import List, Optional


class PaymentSchema(BaseModel):
    user_id: Optional[str] = None
    productid: Optional[str] = None
    price: Optional[float] = None


class Transactions(BaseModel):
    razorpaypaymentid: Optional[str] = None
    user_id: Optional[str] = None
    productid: Optional[str] = None
    price: Optional[float] = None


class TransactionsHistoryUser(BaseModel):
    user_id: Optional[str] = None
