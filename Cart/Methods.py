import uuid
from fastapi import HTTPException, status
from Database_and_ORM.Database_Models import Cart
from .Database_Schemas import CartSchema
from typing import Dict

async def add_to_cart(payload: Dict, cart_data: CartSchema):
  
    userid = cart_data.userid
    productid = cart_data.productid
    price = cart_data.price

   
    if not all([userid, productid, price]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing required fields")

   
    try:
        new_cart_entry = await Cart.create(
            id=uuid.uuid4(),
            userid=userid,
            productid=productid,
            price=price
        )
        return new_cart_entry
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to add to cart: {str(e)}")
