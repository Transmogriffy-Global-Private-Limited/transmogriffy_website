# razorpay_methods/initiate_refund.py

from __future__ import annotations

import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, Any

from fastapi import HTTPException, status
from tortoise.exceptions import DoesNotExist
from razorpay import Client
from decouple import config

from Database_and_ORM.Database_Models import Order, Payments, Refund_Instances, Transactions
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

def _clean_optional_str(value) -> Optional[str]:
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _is_valid_rzp_payment_id(value) -> bool:
    value = _clean_optional_str(value)
    return bool(value and value.startswith("pay_"))


def _same_money(left, right) -> bool:
    try:
        l = Decimal(str(left)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        r = Decimal(str(right)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return l == r
    except Exception:
        return False


async def _resolve_payment_id(order: Order, explicit: Optional[str]) -> str:
    # 1. If caller explicitly passed a real Razorpay payment id, use it.
    explicit = _clean_optional_str(explicit)
    if explicit:
        if not _is_valid_rzp_payment_id(explicit):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid rzp_payment_id: {explicit!r}. Expected Razorpay payment id starting with 'pay_'.",
            )
        return explicit

    # 2. If Order already has a real pay_ id, use it.
    stored_payment_id = _clean_optional_str(getattr(order, "rzp_payment_id", None))
    if _is_valid_rzp_payment_id(stored_payment_id):
        return stored_payment_id

    # 3. Live-flow repair:
    # Current flow stores actual Razorpay payment id in Transactions.razorpaypaymentid.
    matching_transaction = None

    transactions = (
        await Transactions.filter(
            userid=order.userid,
            productid=order.productid,
        )
        .order_by("-created_at")
        .limit(20)
    )

    for tx in transactions:
        tx_payment_id = _clean_optional_str(getattr(tx, "razorpaypaymentid", None))

        if not _is_valid_rzp_payment_id(tx_payment_id):
            continue

        if _same_money(getattr(tx, "price", None), order.totalamount):
            matching_transaction = tx
            break

    if matching_transaction:
        repaired_payment_id = matching_transaction.razorpaypaymentid

        # Repair the order row so the next refund/status call does not need fallback.
        order.rzp_payment_id = repaired_payment_id
        await order.save()

        return repaired_payment_id

    # 4. Stop before Razorpay.
    # This prevents Razorpay "Invalid Request" and gives a clear local error.
    raise HTTPException(
        status_code=400,
        detail=(
            "No valid Razorpay payment id found for this order. "
            f"Order.rzp_payment_id={stored_payment_id!r}. Expected 'pay_...'. "
            "Could not recover matching payment id from Transactions."
        ),
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
