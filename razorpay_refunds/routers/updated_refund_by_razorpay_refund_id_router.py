# razorpay_refunds/routers/update_refund_by_razorpay_refund_id_router.py

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from razorpay_refunds.methods.update_refund_by_razorpay_refund_id import update_refund_by_razorpay_refund_id


router = APIRouter(prefix="/razorpay-refunds", tags=["Razorpay Refunds"])


class UpdateRefundByRzpRefundIdSchema(BaseModel):
    razorpay_refund_id: str  # "rfnd_..."


@router.post("/update-by-rzp-refund-id")
async def update_refund_by_rzp_refund_id_router(payload: UpdateRefundByRzpRefundIdSchema):
    return await update_refund_by_razorpay_refund_id(payload.razorpay_refund_id)
