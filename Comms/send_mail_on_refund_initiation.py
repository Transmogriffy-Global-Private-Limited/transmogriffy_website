# Comms/send_mail_on_refund_initiation.py

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, Any

from decouple import config
from tortoise.exceptions import DoesNotExist

from Database_and_ORM.Database_Models import Order, User, Refund_Instances, Product
from Comms.Methods import send_templated_email


def _paise_to_rupees_str(paise: Optional[int]) -> str:
    """
    Integer paise -> "0.00" rupees string, no float drift.
    If paise is None, returns "0.00".
    """
    if paise is None:
        paise = 0
    rupees = (Decimal(int(paise)) / Decimal(100)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{rupees}"


async def send_mail_on_refund_initiation(
    order_id: str,
    *,
    template_name: str = "refund_initiated",
    brand_name: Optional[str] = None,
    support_email: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Call this after refund initiation (even if status is 'pending' / 'created').
    Uses your DB truth:
      Order -> User -> latest Refund_Instances for that order -> optional Product.
    Sends a templated email.

    Returns a dict; does NOT raise if email fails (refund flow should not break).
    """

    if brand_name is None:
        brand_name = config("BRAND_NAME", default="Transmogriffy")

    if support_email is None:
        support_email = config("SUPPORT_EMAIL", default="tgwbin@gmail.com")

    # 1) Order
    try:
        order = await Order.get(id=order_id)
    except DoesNotExist:
        return {"ok": False, "message": f"Order not found: {order_id}"}

    # 2) User (Order.userid is string UUID)
    try:
        user = await User.get(id=order.userid)
    except DoesNotExist:
        return {"ok": False, "message": f"User not found for order: {order_id}", "user_id": order.userid}

    to_email = getattr(user, "email", None)
    if not to_email:
        return {"ok": False, "message": "User email missing; cannot send refund mail.", "user_id": str(user.id)}

    # 3) Latest refund instance for this order
    refund_row = (
        await Refund_Instances.filter(order_id=str(order.id))
        .order_by("-created_at")
        .first()
    )
    if not refund_row:
        return {"ok": False, "message": f"No refund instance found for order: {order_id}"}

    # 4) Product (optional, but template expects placeholders -> provide safe defaults)
    product_name = ""
    product_model = ""
    try:
        product = await Product.get(id=order.productid)
        product_name = getattr(product, "name", "") or ""
        product_model = getattr(product, "model", "") or ""
    except Exception:
        # keep defaults; email should still send
        pass

    # 5) Values for template (always provide all keys)
    rzp_refund_id = getattr(refund_row, "rzp_refund_id", None) or "N/A"
    refund_status = str(getattr(refund_row, "refund_status", "created"))
    refund_amount_rupees = _paise_to_rupees_str(getattr(refund_row, "refund_amount_paise", 0))
    total_order_amount_rupees = _paise_to_rupees_str(getattr(refund_row, "total_order_amount_paise", 0))

    username = getattr(user, "name", None) or "Customer"

    # 6) Send email (don’t break refund logic if it fails)
    try:
        await send_templated_email(
            to_email=to_email,
            template_name=template_name,

            # REQUIRED placeholders (template below expects exactly these)
            username=username,
            order_id=str(order.id),
            rzp_refund_id=rzp_refund_id,
            refund_status=refund_status,
            refund_amount_rupees=refund_amount_rupees,
            total_order_amount_rupees=total_order_amount_rupees,
            product_name=product_name,
            product_model=product_model,
            brand_name=brand_name,
            support_email=support_email,
        )

        return {
            "ok": True,
            "message": "Refund initiation mail sent.",
            "order_id": str(order.id),
            "to_email": to_email,
            "template_name": template_name,
            "rzp_refund_id": rzp_refund_id,
            "refund_status": refund_status,
        }

    except Exception as e:
        return {
            "ok": False,
            "message": "Refund mail failed to send (refund itself unaffected).",
            "order_id": str(order.id),
            "to_email": to_email,
            "template_name": template_name,
            "error": str(e),
        }
