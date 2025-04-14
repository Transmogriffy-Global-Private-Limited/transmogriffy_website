from fastapi import (
    APIRouter,
    Depends,
    Header,
    status,
    HTTPException,
)
from .Methods import add_to_cart, increase_quantity, decrease_quantity,get_cart,remove_from_cart
from .Database_Schemas import CartSchema, ManagementQuantity,GetCartOfauser

cart_router = APIRouter()


@cart_router.post("/addtocart", status_code=status.HTTP_200_OK)
async def add_to_cart_endpoint(
    cart_data: CartSchema,
):
        result = await add_to_cart({}, cart_data)
        return {"message": "Added to cart successfully"}

@cart_router.post("/getcartdetails", status_code=status.HTTP_200_OK)
async def cart_get(management_data:GetCartOfauser):
        result = await get_cart({},management_data)
        return result
  

# increase the quantity of the product
@cart_router.post("/increasequantity", status_code=status.HTTP_200_OK)
async def increase_quantity_endpoint(
    management_data: ManagementQuantity,
):
        result = await increase_quantity({}, management_data)
        return result


#decrease quantity of the product
@cart_router.post("/decreasemethods", status_code=status.HTTP_200_OK)
async def decrease_quantity_endpoint(
    management_data: ManagementQuantity,
):
        result = await decrease_quantity({}, management_data)
        return result
 

@cart_router.post("/removefromcart", status_code=status.HTTP_200_OK)
async def remove_from_cart_endpoint(
    management_data: ManagementQuantity,
):
    
        result = await remove_from_cart({}, management_data)
        return result

