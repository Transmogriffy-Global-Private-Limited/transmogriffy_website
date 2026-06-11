from pydantic import BaseModel
from typing import Optional
from enum import Enum


# -------------------------
# ORDER STATUS ENUM
# -------------------------
class OrderStatusEnum(str, Enum):
    payment_pending = "payment_pending"
    paid = "paid"
    processing = "processing"
    shipped = "shipped"
    delivered = "delivered"
    cancelled = "cancelled"
    refund_pending = "refund_pending"
    refunded = "refunded"


# -------------------------
# GENERAL ORDER SCHEMA
# (kept because Methods.py imports it)
# -------------------------
class OrderSchema(BaseModel):
    user_id: str
    deliveryaddress: str
    paymentoption: str
    orderstatus: Optional[OrderStatusEnum] = (
        OrderStatusEnum.payment_pending
    )


# -------------------------
# CHECKOUT / CREATE ORDER
# (used in order_create())
# -------------------------
class OrderDupSchema(BaseModel):
    user_id: str
    deliveryaddress: str
    paymentoption: str

    rzp_order_id: str
    rzp_payment_id: str


# -------------------------
# OPTIONAL
# backward compatibility
# -------------------------
class CheckoutSchema(OrderDupSchema):
    pass


# -------------------------
# UPDATE ORDER STATUS
# -------------------------
class OrderStatusSchema(BaseModel):
    orderid: str
    orderstatus: OrderStatusEnum


# -------------------------
# USER ID REQUEST
# -------------------------
class StandAloneUserId(BaseModel):
    user_id: str


# -------------------------
# CANCEL ORDER
# -------------------------
class CancelOrderRequest(BaseModel):
    order_id: str
    reasonforcancel: str
    otherreasonforcancel: Optional[str] = None