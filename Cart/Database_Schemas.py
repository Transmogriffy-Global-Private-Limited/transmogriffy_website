from pydantic import BaseModel, Field
from typing import Optional


class CartSchema(BaseModel):
    # validation_alias accepts 'user_id' from incoming React JSON payloads safely
    user_id: str = Field(..., validation_alias="user_id", description="The unique UUID string of the user")
    
    # validation_alias accepts 'product_id' from frontend but exposes it as 'productid' to match your Methods code
    productid: str = Field(..., validation_alias="product_id", description="The unique UUID string of the product")
    
    price: float = Field(0.0, description="The unit price of the selected item catalog instance")

    class Config:
        populate_by_name = True
        from_attributes = True


class ManagementQuantity(BaseModel):
    user_id: str = Field(..., validation_alias="user_id", description="The unique UUID string of the user")
    productid: str = Field(..., validation_alias="product_id", description="The unique UUID string of the product")
    
    # ✅ FIXED: Marked quantity as Optional with a default fallback of 1 so /removefromcart doesn't throw a 422 error
    quantity: Optional[int] = Field(1, description="The quantity count allocation snapshot")

    class Config:
        populate_by_name = True
        from_attributes = True


class GetCartOfauser(BaseModel):
    user_id: str = Field(..., validation_alias="user_id", description="The unique UUID string of the user to fetch the cart for")

    class Config:
        populate_by_name = True
        from_attributes = True