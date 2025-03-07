from fastapi import (
    APIRouter,
    Depends,
    Header,
    status,
    HTTPException,
)

from .Methods import order_create
from .Data_Schemas import OrderSchema

order_router = APIRouter()


@order_router.post("/addorder", status_code=status.HTTP_200_OK)
async def order_endpoint(order_data: OrderSchema):
    try:
        result = await order_create({}, order_data)
        return {"message": "Order created Successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create order: {str(e)}",
        )
