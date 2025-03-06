from fastapi import (
    APIRouter,
    Depends,
    Header,
    status,
    HTTPException,
)
from .Methods import add_to_cart
from .Database_Schemas import CartSchema

cart_router = APIRouter()

@cart_router.post('/addtocart', status_code=status.HTTP_200_OK)
async def add_to_cart_endpoint(
    cart_data: CartSchema,
):
    try:
        result = await add_to_cart({}, cart_data) 
        return {"message": "Added to cart successfully"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to add to cart: {str(e)}")
