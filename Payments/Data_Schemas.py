from typing import List, Optional
from pydantic import BaseModel, Field


# ----------------------------------------
# Product Item
# ----------------------------------------
class ProductItemSchema(BaseModel):
    productid: str
    quantity: int
    price: Optional[float] = None


# ----------------------------------------
# Transaction Product
# ----------------------------------------
class TransactionProductSchema(BaseModel):
    productid: str
    price: float


# ----------------------------------------
# Create Payment
# ----------------------------------------
class PaymentSchema(BaseModel):
    user_id: str
    products: List[ProductItemSchema]
    price: Optional[float] = None


# ----------------------------------------
# Verify Payment
# ----------------------------------------
class VerifyPaymentSchema(BaseModel):

    razorpay_order_id: str

    razorpay_payment_id: str

    razorpay_signature: str

    user_id: str

    products: List[ProductItemSchema]

    class Config:
        populate_by_name = True
        from_attributes = True


# ----------------------------------------
# Transactions
# ----------------------------------------
class TransactionsSchema(BaseModel):
    user_id: str
    razorpaypaymentid: str
    products: List[TransactionProductSchema]

    class Config:
        from_attributes = True


# ----------------------------------------
# Transaction History
# ----------------------------------------
class TransactionsHistoryUser(BaseModel):
    user_id: str