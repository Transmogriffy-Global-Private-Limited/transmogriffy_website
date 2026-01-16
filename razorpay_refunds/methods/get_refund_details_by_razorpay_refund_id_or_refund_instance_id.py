# methods/get_refund_details_by_razorpay_refund_id_or_refund_instance_id.py

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import HTTPException, status

from Database_and_ORM.Database_Models import Refund_Instances


async def get_refund_details_by_razorpay_refund_id_or_refund_instance_id(
    *,
    razorpay_refund_id: Optional[str] = None,      # "rfnd_..."
    refund_instance_id: Optional[str] = None,      # UUID (Refund_Instances.id)
) -> Dict[str, Any]:
    """
    Fetch a single refund instance details by either:
      - razorpay_refund_id (rzp_refund_id == "rfnd_...") OR
      - refund_instance_id (Refund_Instances.id UUID)

    Rules:
      - Provide exactly one of razorpay_refund_id or refund_instance_id.
      - Returns DB state (does NOT call Razorpay).
    """

    if bool(razorpay_refund_id) == bool(refund_instance_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide exactly one of: razorpay_refund_id, refund_instance_id",
        )

    if razorpay_refund_id:
        row = await Refund_Instances.filter(rzp_refund_id=razorpay_refund_id).first()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No refund found for Razorpay refund id: {razorpay_refund_id}",
            )
    else:
        row = await Refund_Instances.filter(id=refund_instance_id).first()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No refund found for refund_instance_id: {refund_instance_id}",
            )

    return {
        "message": "Refund details fetched from DB.",
        "refund_instance_id": str(row.id),
        "order_id": row.order_id,
        "rzp_payment_id": row.rzp_payment_id,
        "rzp_refund_id": getattr(row, "rzp_refund_id", None),
        "refund_status": row.refund_status,
        "total_order_amount_paise": row.total_order_amount_paise,
        "refund_amount_paise": row.refund_amount_paise,
        "failure_reason": row.failure_reason,
        "created_at": getattr(row, "created_at", None),
        "updated_at": getattr(row, "updated_at", None),
    }
