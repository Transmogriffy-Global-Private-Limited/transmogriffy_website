# methods/fetch_updated_refund_by_id.py

from __future__ import annotations

from typing import Dict, Any, Optional

from fastapi import HTTPException, status
from razorpay import Client
from decouple import config
from tortoise.exceptions import DoesNotExist

from Database_and_ORM.Database_Models import Refund_Instances


# Razorpay refund status enum (exact mirror)
RZP_REFUND_STATUSES = {"created", "pending", "processed", "failed"}


def _rzp_client() -> Client:
    key_id = config("RAZORPAY_KEY_ID", default=None)
    key_secret = config("RAZORPAY_KEY_SECRET", default=None)

    if not key_id or not key_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Razorpay keys are not configured on server.",
        )

    return Client(auth=(key_id, key_secret))


def _looks_like_rzp_unreachable(err: Exception) -> bool:
    """
    We don't want to store initiation/fetch errors as state changes.
    Here we only detect *connectivity/unreachability*.
    """
    msg = (str(err) or "").lower()
    # pragmatic detection: requests/urllib3 style messages
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


async def fetch_updated_refund_by_id(refund_id: str) -> Dict[str, Any]:
    """
    Takes in Razorpay refund_id (rfnd_...).
    1) Reads existing DB row by rzp_refund_id
    2) Fetches latest refund from Razorpay
    3) Updates DB (refund_status + failure_reason when applicable)
    4) Returns updated row

    If Razorpay is unreachable/offline:
      - returns current DB row with message "RZP was not reachable"
      - DB is NOT mutated
    """

    # 0) Load current from DB first (your system truth)
    refund_row = await Refund_Instances.filter(rzp_refund_id=refund_id).first()
    if not refund_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Refund instance not found for Razorpay refund id: {refund_id}",
        )

    # 1) Ask Razorpay for latest
    client = _rzp_client()
    try:
        # Razorpay Python SDK: client.refund.fetch(refundId)
        rzp_refund = client.refund.fetch(refund_id)
    except Exception as e:
        # If RZP offline/unreachable: return current without changing DB
        if _looks_like_rzp_unreachable(e):
            return {
                "message": "RZP was not reachable. Returning last known DB state.",
                "refund_instance_id": str(refund_row.id),
                "order_id": refund_row.order_id,
                "rzp_payment_id": refund_row.rzp_payment_id,
                "rzp_refund_id": refund_row.rzp_refund_id,
                "refund_status": refund_row.refund_status,
                "refund_amount_paise": refund_row.refund_amount_paise,
                "total_order_amount_paise": refund_row.total_order_amount_paise,
                "failure_reason": refund_row.failure_reason,
            }

        # Otherwise: treat as a real error (invalid id, auth issues, etc.)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch refund from Razorpay: {str(e)}",
        )

    # 2) Validate status + update DB (lossless mirror)
    new_status = (rzp_refund.get("status") or "").strip().lower()
    if new_status not in RZP_REFUND_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unknown Razorpay refund status returned: {new_status!r}",
        )

    # Only mutate if something changed (quiet + cheap)
    mutated = False

    if refund_row.refund_status != new_status:
        refund_row.refund_status = new_status
        mutated = True

    # Razorpay fetch payload typically does NOT provide a dedicated failure reason.
    # So: keep existing failure_reason, but if now failed and empty, store a minimal reason.
    if new_status == "failed" and not refund_row.failure_reason:
        refund_row.failure_reason = "Razorpay marked refund status as failed."
        mutated = True

    # If it recovered from failed -> pending/processed, clear failure reason (optional but clean)
    if new_status in {"created", "pending", "processed"} and refund_row.failure_reason:
        refund_row.failure_reason = None
        mutated = True

    if mutated:
        await refund_row.save()

    return {
        "message": "Refund status synced from Razorpay.",
        "refund_instance_id": str(refund_row.id),
        "order_id": refund_row.order_id,
        "rzp_payment_id": refund_row.rzp_payment_id,
        "rzp_refund_id": refund_row.rzp_refund_id,
        "refund_status": refund_row.refund_status,
        "refund_amount_paise": refund_row.refund_amount_paise,
        "total_order_amount_paise": refund_row.total_order_amount_paise,
        "failure_reason": refund_row.failure_reason,
        "razorpay": rzp_refund,  # optional: raw provider payload for debugging
    }
