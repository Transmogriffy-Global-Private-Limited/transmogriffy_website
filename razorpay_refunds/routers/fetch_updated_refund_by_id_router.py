# razorpay_refunds/routers/fetch_updated_refund_by_id_router.py

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from razorpay_refunds.methods.fetch_updated_refund_by_id import fetch_updated_refund_by_id


router = APIRouter(prefix="/razorpay-refunds", tags=["Razorpay Refunds"])


class FetchUpdatedRefundSchema(BaseModel):
    refund_id: str  # Razorpay refund id: "rfnd_..."


@router.post("/fetch-updated")
async def fetch_updated_refund_by_id_router(payload: FetchUpdatedRefundSchema):
    return await fetch_updated_refund_by_id(payload.refund_id)
