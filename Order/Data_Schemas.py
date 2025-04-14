from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class OrderSchema(BaseModel):
    productid: Optional[str] = None
    order_quantity: Optional[str] = None
    userid: Optional[str] = None
    totalamount: Optional[str] = None
    deliveryaddress: Optional[str] = None
    paymentoption: Optional[str] = None
    orderstatus: Optional[str] = None


class OrderDupSchema(BaseModel):
    userid: Optional[str] = None
    cartid: Optional[str] = None
    deliveryaddress: Optional[str] = None

class OrderStatusSchema(BaseModel):
    orderid: Optional[str] = None
    orderstatus: Optional[str] = None

class StandAloneUserId(BaseModel):
    user_id: Optional[str] = None
