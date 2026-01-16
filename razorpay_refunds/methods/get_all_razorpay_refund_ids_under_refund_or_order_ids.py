# methods/get_all_razorpay_refund_ids_under_refund_or_order_ids.py

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status

from Database_and_ORM.Database_Models import Refund_Instances


async def get_all_razorpay_refund_ids_under_refund_or_order_ids(
    *,
    refund_instance_ids: Optional[List[str]] = None,
    order_ids: Optional[List[str]] = None,
    include_rows: bool = False,
) -> Dict[str, Any]:
    """
    Fetch all Razorpay refund ids (rzp_refund_id == "rfnd_...") under:
      - your internal Refund_Instances.id (UUID as str)  OR
      - your internal Order.id (UUID as str, stored in Refund_Instances.order_id)

    Rules:
      - At least one of refund_instance_ids or order_ids must be provided.
      - Only returns rows that have a non-null rzp_refund_id (i.e., actually created at Razorpay).
      - Dedupes refund ids.

    Returns:
      {
        "refund_ids": ["rfnd_..."],
        "count": N,
        "missing_refund_instance_ids": [...],
        "missing_order_ids": [...],
        # optionally "rows": [...]
      }
    """

    refund_instance_ids = refund_instance_ids or []
    order_ids = order_ids or []

    if not refund_instance_ids and not order_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one of: refund_instance_ids, order_ids",
        )

    # Build query: (id IN refund_instance_ids) OR (order_id IN order_ids)
    qs = Refund_Instances.all()

    if refund_instance_ids and order_ids:
        qs = qs.filter(id__in=refund_instance_ids).union(
            Refund_Instances.filter(order_id__in=order_ids)
        )
    elif refund_instance_ids:
        qs = qs.filter(id__in=refund_instance_ids)
    else:
        qs = qs.filter(order_id__in=order_ids)

    rows = await qs

    # Track which ids were actually found (for clear caller feedback)
    found_refund_instance_ids = set()
    found_order_ids = set()

    refund_ids: List[str] = []
    out_rows: List[Dict[str, Any]] = []

    for r in rows:
        found_refund_instance_ids.add(str(r.id))
        found_order_ids.add(str(r.order_id))

        # Only include provider refund id if present
        if getattr(r, "rzp_refund_id", None):
            refund_ids.append(r.rzp_refund_id)

        if include_rows:
            out_rows.append(
                {
                    "refund_instance_id": str(r.id),
                    "order_id": r.order_id,
                    "rzp_payment_id": r.rzp_payment_id,
                    "rzp_refund_id": getattr(r, "rzp_refund_id", None),
                    "refund_status": r.refund_status,
                    "refund_amount_paise": r.refund_amount_paise,
                    "total_order_amount_paise": r.total_order_amount_paise,
                    "failure_reason": r.failure_reason,
                    "created_at": getattr(r, "created_at", None),
                    "updated_at": getattr(r, "updated_at", None),
                }
            )

    # Dedupe while preserving order
    seen = set()
    refund_ids_deduped: List[str] = []
    for rid in refund_ids:
        if rid not in seen:
            seen.add(rid)
            refund_ids_deduped.append(rid)

    missing_refund_instance_ids = [x for x in refund_instance_ids if x not in found_refund_instance_ids]
    missing_order_ids = [x for x in order_ids if x not in found_order_ids]

    resp: Dict[str, Any] = {
        "refund_ids": refund_ids_deduped,
        "count": len(refund_ids_deduped),
        "missing_refund_instance_ids": missing_refund_instance_ids,
        "missing_order_ids": missing_order_ids,
    }

    if include_rows:
        resp["rows"] = out_rows

    return resp
