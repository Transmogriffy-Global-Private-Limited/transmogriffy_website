from pydantic import BaseModel, Field
from typing import Optional


class CartSchema(BaseModel):
    user_id: str = Field(..., description="The unique UUID string of the user")
    product_id: str = Field(..., description="The unique UUID string of the product")  # ✅ FIXED: changed from productid
    price: float = Field(0.0, description="The price of the item")  # ✅ FIXED: changed from Optional[str] to float for calculation safety


class ManagementQuantity(BaseModel):
    user_id: str = Field(..., description="The unique UUID string of the user")
    product_id: str = Field(..., description="The unique UUID string of the product")  # ✅ FIXED: changed from productid
    quantity: int = Field(..., ge=1, description="The quantity must be at least 1")


class GetCartOfauser(BaseModel):
    user_id: str = Field(..., description="The unique UUID string of the user to fetch the cart for")