# razorpay_refunds/routers/get_all_refund_ids_router.py

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from razorpay_refunds.methods.get_all_razorpay_refund_ids_under_refund_or_order_ids import (
    get_all_razorpay_refund_ids_under_refund_or_order_ids,
)


router = APIRouter(prefix="/razorpay-refunds", tags=["Razorpay Refunds"])


class GetAllRefundIdsSchema(BaseModel):
    refund_instance_ids: Optional[List[str]] = None
    order_ids: Optional[List[str]] = None
    include_rows: Optional[bool] = False


@router.post("/get-all-refund-ids")
async def get_all_refund_ids_router(payload: GetAllRefundIdsSchema):
    return await get_all_razorpay_refund_ids_under_refund_or_order_ids(
        refund_instance_ids=payload.refund_instance_ids,
        order_ids=payload.order_ids,
        include_rows=bool(payload.include_rows),
    )
