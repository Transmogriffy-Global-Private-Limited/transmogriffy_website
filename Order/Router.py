from fastapi import APIRouter, Depends, Header, status, HTTPException, Body
from pydantic import BaseModel, Field
from typing import Optional

from .Methods import (
    order_create, 
    order_history, 
    order_status_update, 
    get_allorders, 
    cancel_order
)
from .Data_Schemas import (
    CheckoutSchema,
    StandAloneUserId,
    OrderStatusSchema
)

order_router = APIRouter()


class CancelOrderRequest(BaseModel):
    order_id: str = Field(..., description="The unique UUID string of the order to cancel")
    reasonforcancel: str = Field(..., description="The primary classification reason for cancellation")
    otherreasonforcancel: Optional[str] = Field(None, description="Custom details if reasonforcancel is set to 'other'")


@order_router.post("/orderhistory", status_code=status.HTTP_200_OK)
async def get_order_history(request: StandAloneUserId):
    try:
        return await order_history(request.user_id)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch order history: {str(e)}"
        )
    
@order_router.post(
    "/addorder",
    status_code=200
)
async def create_order(
    payload: CheckoutSchema
):
    return await order_create(
        payload
    )

@order_router.post("/statusupdate", status_code=status.HTTP_200_OK)
async def update_order_status(status_data: OrderStatusSchema):
    try:
        return await order_status_update(status_data)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute order status mutation: {str(e)}"
        )


@order_router.get("/allorderdata", status_code=status.HTTP_200_OK)
async def list_of_orders():
    try:
        return await get_allorders()
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve global system orders: {str(e)}"
        )


@order_router.post("/cancelorder", status_code=status.HTTP_200_OK)
async def cancel_order_endpoint(payload: CancelOrderRequest):
    try:
        return await cancel_order(
            order_id=payload.order_id, 
            reasonforcancel=payload.reasonforcancel, 
            otherreasonforcancel=payload.otherreasonforcancel
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute order cancellation workflow: {str(e)}"
        )