from fastapi import (
    APIRouter,
    Depends,
    Header,
    status,
    HTTPException,
)
from .Methods import add_to_cart, increase_quantity, decrease_quantity
from .Database_Schemas import CartSchema, ManagementQuantity

cart_router = APIRouter()


@cart_router.post("/addtocart", status_code=status.HTTP_200_OK)
async def add_to_cart_endpoint(
    cart_data: CartSchema,
):
    try:
        result = await add_to_cart({}, cart_data)
        return {"message": "Added to cart successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add to cart: {str(e)}",
        )

# increase the quantity of the product
@cart_router.post("/increasequantity", status_code=status.HTTP_200_OK)
async def increase_quantity_endpoint(
    management_data: ManagementQuantity,
):
    try:
        result = await increase_quantity({}, management_data)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to increase quantity: {str(e)}",
        )

#decrease quantity of the product
@cart_router.post("/decreasemethods", status_code=status.HTTP_200_OK)
async def decrease_quantity_endpoint(
    management_data: ManagementQuantity,
):
    try:
        result = await decrease_quantity({}, management_data)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to decrease quantity: {str(e)}",
        )
