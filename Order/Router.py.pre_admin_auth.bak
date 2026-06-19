from fastapi import APIRouter, Depends, Header, status, HTTPException, Body
from Utility_Methods.Utility_Methods import (
    verify_jwt,
    verify_admin_jwt,
    get_authenticated_actor,
)
from Database_and_ORM.Database_Models import Order
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
async def get_order_history(
    request: StandAloneUserId,
    actor: dict = Depends(get_authenticated_actor),
):
    if actor["role"] != "admin" and str(actor["id"]) != str(request.user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot view another user's order history",
        )
    try:
        return await order_history(request.user_id)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch order history: {str(e)}"
        )
    
async def create_order(
    payload: CheckoutSchema,
    actor: dict = Depends(get_authenticated_actor),
):
    if actor["role"] != "admin" and str(actor["id"]) != str(payload.user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create an order for another user",
        )

    return await order_create(payload)

@order_router.post("/statusupdate", status_code=status.HTTP_200_OK)
async def update_order_status(
    status_data: OrderStatusSchema,
    admin_payload: dict = Depends(verify_admin_jwt),
):


@order_router.get("/allorderdata", status_code=status.HTTP_200_OK)
async def list_of_orders(admin_payload: dict = Depends(verify_admin_jwt)):


@order_router.post("/cancelorder", status_code=status.HTTP_200_OK)
async def cancel_order_endpoint(
    payload: CancelOrderRequest,
    actor: dict = Depends(get_authenticated_actor),
):
    order = await Order.get_or_none(id=payload.order_id)

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    if actor["role"] != "admin" and str(order.userid) != str(actor["id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot cancel another user's order",
        )

    return await cancel_order(
        order_id=payload.order_id,
        reasonforcancel=payload.reasonforcancel,
        otherreasonforcancel=payload.otherreasonforcancel,
    )