from fastapi import (
    APIRouter,
    Depends,
    Header,
    status,
    HTTPException,
)
from .Methods import (
    add_to_cart, 
    increase_quantity, 
    decrease_quantity, 
    get_cart, 
    remove_from_cart
)
from .Database_Schemas import CartSchema, ManagementQuantity, GetCartOfauser

cart_router = APIRouter()


@cart_router.post("/addtocart", status_code=status.HTTP_200_OK)
async def add_to_cart_endpoint(cart_data: CartSchema):
    try:
        result = await add_to_cart({}, cart_data)
        return {"message": "Added to cart successfully"}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Router Error: {str(e)}"
        )


@cart_router.post("/getcartdetails", status_code=status.HTTP_200_OK)
async def cart_get(management_data: GetCartOfauser):
    try:
        result = await get_cart({}, management_data)
        return result
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Router Error: {str(e)}"
        )


# Increase the quantity of the product
@cart_router.post("/increasequantity", status_code=status.HTTP_200_OK)
async def increase_quantity_endpoint(management_data: ManagementQuantity):
    try:
        result = await increase_quantity({}, management_data)
        return result
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Router Error: {str(e)}"
        )


# Decrease quantity of the product
@cart_router.post("/decreasemethods", status_code=status.HTTP_200_OK)
async def decrease_quantity_endpoint(management_data: ManagementQuantity):
    try:
        result = await decrease_quantity({}, management_data)
        return result
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Router Error: {str(e)}"
        )


@cart_router.post("/removefromcart", status_code=status.HTTP_200_OK)
async def remove_from_cart_endpoint(management_data: ManagementQuantity):
    try:
        result = await remove_from_cart({}, management_data)
        return result
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Router Error: {str(e)}"
        )