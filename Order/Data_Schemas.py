from enum import Enum
from typing import Optional, List
from pydantic import BaseModel

# -----------------------------------------------------------------------------
# ORDER STATUS ENUM
# -----------------------------------------------------------------------------
class OrderStatusEnum(str, Enum):
    payment_pending = "payment_pending"
    paid = "paid"
    processing = "processing"
    shipped = "shipped"
    delivered = "delivered"
    cancelled = "cancelled"
    refund_pending = "refund_pending"
    refunded = "refunded"

# -----------------------------------------------------------------------------
# CHECKOUT INTERFACES
# -----------------------------------------------------------------------------
class ProductItemSchema(BaseModel):
    productid: str
    quantity: int

class CheckoutSchema(BaseModel):
    user_id: str
    deliveryaddress: str
    paymentoption: str
    # If your front-end passes the items in the body payload explicitly, leave this line active.
    # If the front-end ONLY sends user_id and expects the backend to pull the cart, comment this line out!
    products: Optional[List[ProductItemSchema]] = None 

# -----------------------------------------------------------------------------
# BACKWARD COMPATIBILITY LAYERS
# -----------------------------------------------------------------------------
class OrderSchema(CheckoutSchema):
    orderstatus: Optional[OrderStatusEnum] = OrderStatusEnum.payment_pending

class OrderDupSchema(BaseModel):
    user_id: str
    deliveryaddress: str
    paymentoption: str
    rzp_order_id: str
    rzp_payment_id: str

# -----------------------------------------------------------------------------
# LIFECYCLE MANAGEMENT UTILITIES
# -----------------------------------------------------------------------------
class OrderStatusSchema(BaseModel):
    orderid: str
    orderstatus: OrderStatusEnum

class StandAloneUserId(BaseModel):
    user_id: str

class CancelOrderRequest(BaseModel):
    order_id: str
    reasonforcancel: str
    otherreasonforcancel: Optional[str] = None