from fastapi import APIRouter, Depends, Header, status, HTTPException, Body

from .Methods import order_create, order_history, order_status_update,get_allorders,cancel_order
from .Data_Schemas import OrderDupSchema, StandAloneUserId,OrderStatusSchema
from pydantic import BaseModel

order_router = APIRouter()



class CancelOrderRequest(BaseModel):
    order_id: str
    reasonforcancel: str


@order_router.post("/addorder", status_code=status.HTTP_200_OK)
async def order_endpoint(order_data: OrderDupSchema):
        result = await order_create({}, order_data)
        return {"message": "Order created Successfully"}

@order_router.post("/orderhistory", status_code=status.HTTP_200_OK)
async def get_order_history(request: StandAloneUserId):
    try:
        order_history_data = await order_history(request.user_id)
        return order_history_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch order history: {str(e)}",
        )

@order_router.post("/statusupdate", status_code=status.HTTP_200_OK)
async def update_order_status(status_data: OrderStatusSchema):
    return await order_status_update(status_data)

@order_router.get("/allorderdata",status_code = status.HTTP_200_OK)
async def list_of_orders():
    return await get_allorders()

@order_router.post("/cancelorder", status_code=status.HTTP_200_OK)
async def cancel_order_endpoint(payload: CancelOrderRequest):
    return await cancel_order(payload.order_id,payload.reasonforcancel)