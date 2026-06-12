from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

# -----------------------------------------------------------------------------
# CORE ORDER LIFECYCLE SCHEMAS
# -----------------------------------------------------------------------------
class OrderSchema(BaseModel):
    user_id: Optional[str] = None
    product_id: Optional[str] = None
    ordered_quantity: Optional[str] = None
    totalamount: Optional[str] = None
    deliveryaddress: Optional[str] = None
    paymentoption: Optional[str] = None
    orderstatus: Optional[str] = None

    class Config:
        from_attributes = True


class OrderDupSchema(BaseModel):
    user_id: Optional[str] = None
    cart_id: Optional[str] = None
    deliveryaddress: Optional[str] = None
    paymentoption: Optional[str] = None
    rzp_payment_id: Optional[str] = None
    rzp_order_id: Optional[str] = None
    orderstatus: Optional[str] = None

    class Config:
        from_attributes = True


class OrderStatusSchema(BaseModel):
    orderid: Optional[str] = None
    orderstatus: Optional[str] = None


class CheckoutSchema(BaseModel):
    user_id: str = Field(..., description="The unique customer UUID reference identifier")
    deliveryaddress: str = Field(..., description="The clear text delivery target address")
    paymentoption: str = Field(default="razorpay", description="The engine gateway option selected")


class StandAloneUserId(BaseModel):
    user_id: Optional[str] = None


# -----------------------------------------------------------------------------
# CORE PAYMENT & TRANSACTION LIFECYCLE SCHEMAS
# -----------------------------------------------------------------------------
class ProductItemSchema(BaseModel):
    productid: str = Field(..., description="The target product inventory item UUID reference string")
    quantity: int = Field(..., g=1, description="The integer count allocation quantity")


class PaymentSchema(BaseModel):
    user_id: str = Field(..., description="The core user identity reference tracking anchor token")
    products: List[ProductItemSchema] = Field(..., description="The snapshot manifest collection list array")


class VerifyPaymentSchema(BaseModel):
    razorpay_order_id: str = Field(..., description="The payment intent tracking reference string")
    razorpay_payment_id: str = Field(..., description="The success reference token string capture")
    razorpay_signature: str = Field(..., description="The cryptographic validation check authentication value")


class TransactionsSchema(BaseModel):
    id: str
    user_id: str
    razorpaypaymentid: str
    price: str


class TransactionsHistoryUser(BaseModel):
    user_id: str = Field(..., description="Target query context profile reference token")