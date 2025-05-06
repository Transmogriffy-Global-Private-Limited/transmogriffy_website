from typing import Optional
from pydantic import BaseModel, Field


class BuyNowSchema(BaseModel):
    user_id: Optional[str] = Field(None, description="ID of the user initiating the purchase")
    product_id: Optional[str] = Field(None, description="ID of the product being purchased")
    address_id: Optional[str] = Field(None, description="ID of the delivery address")
    quantity: Optional[int] = Field(1, description="Quantity of the product being purchased", ge=1)
    price: Optional[float] = Field(None, description="Total price for the purchase", gt=0)
    payment_method: Optional[str] = Field(None, description="Payment method used for the transaction")
    order_status: Optional[str] = Field(None, description="Current status of the order, e.g., 'Pending', 'Completed', 'Cancelled'")

class PaymentSchema(BaseModel):
    user_id: Optional[str] = None
    products: Optional[str]=None
    price: Optional[float] = None


class TransactionsSchema(BaseModel):
    user_id: Optional[str] = None
    razorpaypaymentid: Optional[str] = None
    products: Optional[str]=None

class OrderSchema(BaseModel):
    productid: Optional[str] = None
    order_quantity: Optional[str] = None
    userid: Optional[str] = None
    totalamount: Optional[str] = None
    deliveryaddress: Optional[str] = None
    paymentoption: Optional[str] = None
    orderstatus: Optional[str] = None


class OrderDupSchema(BaseModel):
    user_id: Optional[str] = None
    cartid: Optional[str] = None
    deliveryaddress: Optional[str] = None
    paymentoption: Optional[str] = None
    orderstatus: Optional[str] = None