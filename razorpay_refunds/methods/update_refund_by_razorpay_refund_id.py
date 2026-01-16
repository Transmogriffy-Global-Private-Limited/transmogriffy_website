# methods/update_refund_by_razorpay_refund_id.py

from __future__ import annotations

from typing import Any, Dict

from fastapi import HTTPException, status
from razorpay import Client
from decouple import config

from Database_and_ORM.Database_Models import Refund_Instances


RZP_REFUND_STATUSES = {"created", "pending", "processed", "failed"}


def _rzp_client() -> Client:
    key_id = config("RAZOR_PAY_KEY", default=None)
    key_secret = config("RAZOR_PAY_SECRET", default=None)

    if not key_id or not key_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Razorpay keys are not configured on server.",
        )

    return Client(auth=(key_id, key_secret))


def _looks_like_rzp_unreachable(err: Exception) -> bool:
    msg = (str(err) or "").lower()
    offline_signatures = [
        "timed out",
        "timeout",
        "max retries exceeded",
        "connection aborted",
        "failed to establish a new connection",
        "name or service not known",
        "temporary failure in name resolution",
        "network is unreachable",
        "connection reset by peer",
        "connection refused",
        "read timed out",
        "ssl",
    ]
    return any(sig in msg for sig in offline_signatures)


async def update_refund_by_razorpay_refund_id(razorpay_refund_id: str) -> Dict[str, Any]:
    """
    Calls Razorpay to fetch current refund state for the given rzp_refund_id ("rfnd_...").
    Updates DB only if Razorpay is reachable and returns a valid status.

    If Razorpay is unreachable, DB is NOT mutated and the current DB row is returned with a message.
    """

    row = await Refund_Instances.filter(rzp_refund_id=razorpay_refund_id).first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No refund instance found for Razorpay refund id: {razorpay_refund_id}",
        )

    client = _rzp_client()

    try:
        rzp_refund = client.refund.fetch(razorpay_refund_id)
    except Exception as e:
        if _looks_like_rzp_unreachable(e):
            return {
                "message": "RZP was not reachable. DB not updated; returning last known DB state.",
                "refund_instance_id": str(row.id),
                "order_id": row.order_id,
                "rzp_payment_id": row.rzp_payment_id,
                "rzp_refund_id": row.rzp_refund_id,
                "refund_status": row.refund_status,
                "total_order_amount_paise": row.total_order_amount_paise,
                "refund_amount_paise": row.refund_amount_paise,
                "failure_reason": row.failure_reason,
            }

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch refund from Razorpay: {str(e)}",
        )

    new_status = (rzp_refund.get("status") or "").strip().lower()
    if new_status not in RZP_REFUND_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unknown Razorpay refund status returned: {new_status!r}",
        )

    mutated = False

    if row.refund_status != new_status:
        row.refund_status = new_status
        mutated = True

    # Razorpay doesn't reliably give a "failure reason" string.
    # Keep it simple + deterministic:
    if new_status == "failed":
        if not row.failure_reason:
            row.failure_reason = "Razorpay marked refund status as failed."
            mutated = True
    else:
        if row.failure_reason:
            row.failure_reason = None
            mutated = True

    if mutated:
        await row.save()

    return {
        "message": "Refund updated from Razorpay." if mutated else "Refund already up-to-date.",
        "refund_instance_id": str(row.id),
        "order_id": row.order_id,
        "rzp_payment_id": row.rzp_payment_id,
        "rzp_refund_id": row.rzp_refund_id,
        "refund_status": row.refund_status,
        "total_order_amount_paise": row.total_order_amount_paise,
        "refund_amount_paise": row.refund_amount_paise,
        "failure_reason": row.failure_reason,
        "razorpay": rzp_refund,  # optional raw payload
    }
