from fastapi import APIRouter, Depends, Header, status, HTTPException, Body

from .Methods import order_create, order_history, order_status_update,get_allorders,cancel_order
from .Data_Schemas import OrderDupSchema, StandAloneUserId,OrderStatusSchema
from pydantic import BaseModel
from typing import Optional
from .Data_Schemas import (
    CheckoutSchema,
    StandAloneUserId,
    OrderStatusSchema
)
order_router = APIRouter()



class CancelOrderRequest(BaseModel):
    order_id: Optional[str] = None
    reasonforcancel: Optional[str] = None
    otherreasonforcancel: Optional[str] = None


#@order_router.post("/addorder", status_code=status.HTTP_200_OK)
#async def order_endpoint(order_data: OrderDupSchema):
 #       result = await order_create({}, order_data)
 #       return {"message": "Order created Successfully"}




@order_router.post("/checkout", status_code=status.HTTP_201_CREATED)
async def checkout(order_data: CheckoutSchema):
    try:
        return await order_create(order_data)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Checkout initialization failed: {str(e)}"
        )

@order_router.post("/orderhistory", status_code=status.HTTP_200_OK)
async def get_order_history(request: StandAloneUserId):
    return await order_history(request.user_id)

@order_router.post("/statusupdate", status_code=status.HTTP_200_OK)
async def update_order_status(status_data: OrderStatusSchema):
    return await order_status_update(status_data)

@order_router.get("/allorderdata", status_code=status.HTTP_200_OK)
async def list_of_orders():
    return await get_allorders()

@order_router.post("/cancelorder", status_code=status.HTTP_200_OK)
async def cancel_order_endpoint(payload: CancelOrderRequest):
    return await cancel_order(payload.order_id, payload.reasonforcancel, payload.otherreasonforcancel)