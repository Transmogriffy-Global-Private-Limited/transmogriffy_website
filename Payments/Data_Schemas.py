from tortoise import fields
from enum import Enum
from pydantic import BaseModel, UUID4, Field
from typing import List, Optional

class PaymentSchema(BaseModel):
    userid:Optional[str] = None
    productid: Optional[str] = None
    price: Optional[float]  = None

class Transactions(BaseModel):
   razorpaypaymentid: Optional[str] = None
   userid: Optional[str] = None
   productid:Optional[str] = None
   price:Optional[float] = None

class TransactionsHistoryUser(BaseModel):
    userid:Optional[str] = None