# razorpay_refunds/routers/initiate_refund_router.py

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from razorpay_refunds.methods.initiate_refund import initiate_refund


router = APIRouter(prefix="/razorpay-refunds", tags=["Razorpay Refunds"])


class InitiateRefundSchema(BaseModel):
    order_id: str

    # Optional: partial refund support (in paise)
    refund_amount_paise: Optional[int] = None

    # Optional: allow FE to pass known payment id
    rzp_payment_id: Optional[str] = None

    # Optional: stored in Razorpay notes, not in DB (DB is updated by webhook later)
    reason: Optional[str] = None


@router.post("/initiate")
async def initiate_refund_router(payload: InitiateRefundSchema):
    return await initiate_refund(
        order_id=payload.order_id,
        refund_amount_paise=payload.refund_amount_paise,
        rzp_payment_id=payload.rzp_payment_id,
        reason=payload.reason,
    )
