# razorpay_refunds/routers/get_refund_details_router.py

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from razorpay_refunds.methods.get_refund_details_by_razorpay_refund_id_or_refund_instance_id import (
    get_refund_details_by_razorpay_refund_id_or_refund_instance_id,
)

router = APIRouter(prefix="/razorpay-refunds", tags=["Razorpay Refunds"])


class GetRefundDetailsSchema(BaseModel):
    razorpay_refund_id: Optional[str] = None   # "rfnd_..."
    refund_instance_id: Optional[str] = None   # UUID


@router.post("/get-refund-details")
async def get_refund_details_router(payload: GetRefundDetailsSchema):
    return await get_refund_details_by_razorpay_refund_id_or_refund_instance_id(
        razorpay_refund_id=payload.razorpay_refund_id,
        refund_instance_id=payload.refund_instance_id,
    )
