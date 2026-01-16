# razorpay_methods/initiate_refund.py

from __future__ import annotations

import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, Any

from fastapi import HTTPException, status
from tortoise.exceptions import DoesNotExist
from razorpay import Client
from decouple import config

from Database_and_ORM.Database_Models import Order, Payments, Refund_Instances
from Comms.send_mail_on_refund_initiation import send_mail_on_refund_initiation


RZP_REFUND_STATUSES = {"created", "pending", "processed", "failed"}


def _to_paise(value_rupees_like: str | int | float | Decimal) -> int:
    d = Decimal(str(value_rupees_like)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    paise = int((d * 100).to_integral_value(rounding=ROUND_HALF_UP))
    if paise < 0:
        raise HTTPException(status_code=400, detail="Amount cannot be negative.")
    return paise


def _rzp_client() -> Client:
    key_id = config("RAZOR_PAY_KEY", default=None)
    key_secret = config("RAZOR_PAY_SECRET", default=None)
    if not key_id or not key_secret:
        raise HTTPException(status_code=500, detail="Razorpay keys not configured.")
    return Client(auth=(key_id, key_secret))

async def _resolve_payment_id(order: Order, explicit: Optional[str]) -> str:
    if explicit:
        return explicit

    if getattr(order, "rzp_payment_id", None):
        return order.rzp_payment_id

    raise HTTPException(
        status_code=404,
        detail="No rzp_payment_id attached to this order. Cannot initiate refund."
    )

async def initiate_refund(
    order_id: str,
    *,
    refund_amount_paise: Optional[int] = None,
    rzp_payment_id: Optional[str] = None,
    reason: Optional[str] = None,
) -> Dict[str, Any]:

    # 1) Order
    try:
        order = await Order.get(id=order_id)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found.")

    if order.orderstatus != "canceled":
        raise HTTPException(
            status_code=400,
            detail=f"Refund allowed only for canceled orders. Current: '{order.orderstatus}'."
        )

    if not getattr(order, "totalamount", None):
        raise HTTPException(status_code=400, detail="Order totalamount missing; cannot refund.")

    total_paise = _to_paise(order.totalamount)
    if refund_amount_paise is None:
        refund_amount_paise = total_paise

    if refund_amount_paise <= 0:
        raise HTTPException(status_code=400, detail="Refund amount must be > 0 paise.")
    if refund_amount_paise > total_paise:
        raise HTTPException(status_code=400, detail="Refund amount cannot exceed total order amount.")

    # 2) Guard ONLY against duplicate “in-flight” or already “processed”
    # Failed does NOT block (your rule) — retries create new row.
    existing_active = (
        await Refund_Instances.filter(
            order_id=str(order.id),
            refund_amount_paise=refund_amount_paise,
            refund_status__in=["created", "pending", "processed"],
        )
        .order_by("-created_at")
        .first()
    )
    if existing_active:
        return {
            "message": "Refund already active/completed for this order+amount.",
            "refund_instance_id": str(existing_active.id),
            "order_id": existing_active.order_id,
            "rzp_payment_id": existing_active.rzp_payment_id,
            "rzp_refund_id": existing_active.rzp_refund_id,
            "refund_status": existing_active.refund_status,
            "refund_amount_paise": existing_active.refund_amount_paise,
            "total_order_amount_paise": existing_active.total_order_amount_paise,
            "failure_reason": existing_active.failure_reason,
        }

    # 3) Resolve payment id
    payment_id = await _resolve_payment_id(order, rzp_payment_id)

    # 4) Call Razorpay FIRST (because you don't want initiation failures stored)
    client = _rzp_client()
    payload: Dict[str, Any] = {"amount": int(refund_amount_paise)}
    if reason:
        payload["notes"] = {"reason": reason}

    try:
        rzp_refund = client.payment.refund(payment_id, payload)
    except Exception as e:
        # IMPORTANT: No DB write here
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Refund initiation failed from Razorpay: {str(e)}",
        )

    # 5) Validate + persist (new UUID every time; even after previous failures)
    rzp_refund_id = rzp_refund.get("id")
    rzp_status = (rzp_refund.get("status") or "").strip().lower()

    if rzp_status not in RZP_REFUND_STATUSES:
        raise HTTPException(status_code=502, detail=f"Unknown Razorpay refund status: {rzp_status!r}")
    if not rzp_refund_id:
        raise HTTPException(status_code=502, detail="Razorpay refund id missing in response.")

    refund_row = await Refund_Instances.create(
        id=uuid.uuid4(),
        order_id=str(order.id),
        rzp_payment_id=payment_id,
        rzp_refund_id=rzp_refund_id,
        total_order_amount_paise=total_paise,
        refund_amount_paise=refund_amount_paise,
        refund_status=rzp_status,
        failure_reason=None,  # webhook can later set failure_reason if it becomes failed
    )

    try:
        await send_mail_on_refund_initiation(str(order.id))
    except Exception as mail_err:
        # Do NOT break refund flow because email failed
        print(f"[refund-mail] Failed to send refund initiation mail: {mail_err}")

    return {
        "message": "Refund initiated (Razorpay accepted).",
        "refund_instance_id": str(refund_row.id),
        "order_id": refund_row.order_id,
        "rzp_payment_id": refund_row.rzp_payment_id,
        "rzp_refund_id": refund_row.rzp_refund_id,
        "refund_status": refund_row.refund_status,
        "refund_amount_paise": refund_row.refund_amount_paise,
        "total_order_amount_paise": refund_row.total_order_amount_paise,
        "razorpay": rzp_refund,
    }
