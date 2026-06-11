import uuid
import random
import logging
import razorpay
from fastapi import HTTPException, status
from tortoise.exceptions import DoesNotExist, IntegrityError
from tortoise.transactions import in_transaction
from decouple import config

from .Data_Schemas import CheckoutSchema, OrderStatusSchema
from Database_and_ORM.Database_Models import Order, Cart, Product, User, Refund_Instances
from Comms.Methods import send_templated_email
from razorpay_refunds.methods.initiate_refund import initiate_refund

logger = logging.getLogger(__name__)

# Razorpay client engine initialization
razorpay_client = razorpay.Client(
    auth=(config("RAZOR_PAY_KEY"), config("RAZOR_PAY_SECRET"))
)

# -----------------------------------------------------------------------------
# 1. CREATE INITIAL PENDING ORDER & LINK RAZORPAY INTENT
# -----------------------------------------------------------------------------
async def order_create(order_data: CheckoutSchema):
    try:
        # Step A: Validate active context customer profiles
        user = await User.get(id=order_data.user_id)

        # Step B: Load current user cart line-items intent snapshots
        cart_items = await Cart.filter(userid=order_data.user_id).all()
        if not cart_items:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cannot instantiate checkouts against empty digital carts."
            )

        total_amount = 0.0
        order_items_manifest = []

        # Step C: Pre-flight stock calculations and absolute financial summaries safely
        for item in cart_items:
            product = await Product.get(id=item.productid)
            if product.quantity < int(item.quantity):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Inventory limit exceeded for {product.name}. Insufficient stock availability."
                )
            
            line_total = float(product.price) * int(item.quantity)
            total_amount += line_total
            order_items_manifest.append({
                "productid": item.productid,
                "quantity": int(item.quantity),
                "price": line_total
            })

        # Step D: Contact Razorpay Payment API gateway to request secure Order Token
        # Multiply total_amount by 100 to cast floats safely into whole numbers (paise)
        razorpay_order_payload = {
            "amount": int(total_amount * 100),  
            "currency": "INR",
            "receipt": f"rcpt_internal_{random.randint(10000, 99999)}",
            "notes": {
                "user_id": str(user.id),
                "delivery_address": order_data.deliveryaddress
            }
        }
        
        rzp_order = razorpay_client.order.create(data=razorpay_order_payload)

        created_orders = []

        # Step E: Commit state entries into persistent store inside safe context bounds
        async with in_transaction() as connection:
            for item in order_items_manifest:
                # Build an open-ended tracked placeholder reference order 
                new_order = await Order.create(
                    id=uuid.uuid4(),
                    userid=str(user.id),
                    productid=item["productid"],
                    ordered_quantity=str(item["quantity"]), # Converted to str to match legacy model
                    totalamount=str(item["price"]),
                    paymentoption=order_data.paymentoption,
                    deliveryaddress=order_data.deliveryaddress,
                    orderstatus="payment_pending",     # Explicit starting checkpoint state
                    rzp_order_id=rzp_order["id"],      # Capture tracking link string
                    rzp_payment_id="none",             # Empty until validation clears
                    using_db=connection
                )
                created_orders.append(new_order)

        return {
            "message": "Internal checkout pending order generated successfully.",
            "internal_orders_count": len(created_orders),
            "razorpay_order_id": rzp_order["id"],
            "amount_paise": rzp_order["amount"],
            "currency": rzp_order["currency"],
            "orders": [{"order_id": str(o.id), "product_id": str(o.productid)} for o in created_orders]
        }

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Target User or Product model entry records not found.")
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Critical breakdown during transaction workflow execution initialization: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Checkout creation workflow broke down: {str(e)}")

# -----------------------------------------------------------------------------
# 2. UPDATE ORDER STATUS (Guarded Transitions)
# -----------------------------------------------------------------------------
async def order_status_update(order_status: OrderStatusSchema):
    try:
        ALLOWED_TRANSITIONS = {
            "payment_pending": ["paid", "cancelled"],
            "paid": ["processing", "refund_pending"],
            "processing": ["shipped", "cancelled"],
            "shipped": ["delivered"],
            "refund_pending": ["refunded"]
        }

        order = await Order.get(id=order_status.orderid)
        current_status = str(order.orderstatus).lower() if order.orderstatus else "payment_pending"
        requested_status = str(order_status.orderstatus).lower()

        if requested_status not in ALLOWED_TRANSITIONS.get(current_status, []):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Protected lifecycle transition error. Cannot process state mutation '{current_status}' → '{requested_status}'."
            )

        old_status = order.orderstatus
        order.orderstatus = requested_status
        await order.save()

        try:
            userdata = await User.get(id=order.userid)
            product = await Product.get(id=order.productid)
            await send_templated_email(
                to_email=userdata.email,
                template_name="updatedorder",
                username=userdata.name,
                order_id=str(order.id),
                old_status=str(old_status),
                new_status=str(order.orderstatus),
                product_name=product.name,
                product_model=product.model,
                quantity=str(order.ordered_quantity)
            )
        except Exception as mail_err:
            logger.warning(f"Asynchronous notification broadcast skipped: {str(mail_err)}")

        return {
            "message": "Status updated successfully.",
            "order_id": str(order.id),
            "old_status": old_status,
            "new_status": order.orderstatus
        }

    except DoesNotExist:
        raise HTTPException(status_code=404, detail=f"Target Order id reference '{order_status.orderid}' absent.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------------------------------------------------------
# 3. CANCEL ORDER & REVERT TRANSACTION LIFECYCLES
# -----------------------------------------------------------------------------
async def cancel_order(order_id: str, reasonforcancel: str, otherreasonforcancel: str):
    try:
        if not reasonforcancel:
            raise HTTPException(status_code=400, detail="Cancellation tracking reason required.")

        final_reason = reasonforcancel
        custom_reason = otherreasonforcancel if str(reasonforcancel).lower() == "other" else None

        if str(reasonforcancel).lower() == "other" and not otherreasonforcancel:
            raise HTTPException(status_code=400, detail="Please clarify custom explanations inside otherreasonforcancel.")

        order = await Order.get(id=order_id)
        current_status = str(order.orderstatus).lower() if order.orderstatus else "payment_pending"

        if current_status in ["cancelled", "canceled"]:
            return {"message": "Order execution record is already marked as inactive.", "order_id": str(order.id)}

        if current_status not in ["payment_pending", "paid", "processing"]:
            raise HTTPException(
                status_code=400,
                detail=f"Active processing blocks prevent cancellation from state profile '{current_status}'."
            )

        async with in_transaction() as connection:
            order.orderstatus = "cancelled"
            order.reasonforcancel = final_reason
            order.otherreasonforcancel = custom_reason
            await order.save(using_db=connection)

            if current_status in ["paid", "processing"]:
                product = await Product.get(id=order.productid)
                await Product.filter(id=order.productid).update(
                    quantity=product.quantity + int(order.ordered_quantity)
                )

        refund_status = "not_required"
        if current_status in ["paid", "processing"]:
            try:
                await initiate_refund(order_id)
                refund_status = "initiated"
            except Exception as e:
                logger.error(f"Automatic financial rollover processing execution sequence broke down: {str(e)}")
                refund_status = "failed_manual_intervention_required"

        try:
            user = await User.get(id=order.userid)
            product = await Product.get(id=order.productid)
            reason_text = f"{final_reason}\n{custom_reason}" if custom_reason else final_reason
            await send_templated_email(
                to_email=user.email,
                template_name="canceledorder",
                username=user.name,
                order_id=str(order.id),
                product_name=product.name,
                product_model=product.model,
                quantity=str(order.ordered_quantity),
                reason=reason_text
            )
        except Exception as mail_err:
            logger.warning(f"Cancellation email delivery failed: {str(mail_err)}")

        return {
            "message": "Order cancelled successfully.",
            "order_id": str(order.id),
            "status": order.orderstatus,
            "refund": refund_status
        }

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Target order reference data matching parameter keys missing.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cancellation transaction rolled back: {str(e)}")

# -----------------------------------------------------------------------------
# 4. READ COMPREHENSIVE SYSTEM ORDER RECORDS
# -----------------------------------------------------------------------------
async def get_allorders():
    try:
        orders = await Order.all()
        refund_rows = await Refund_Instances.all()
        refunds_by_order_id = {}

        for refund in refund_rows:
            order_id_key = str(refund.order_id)
            refund_status = refund.refund_status.value if hasattr(refund.refund_status, "value") else refund.refund_status
            
            refund_details = {
                "refund_instance_id": str(refund.id),
                "order_id": str(refund.order_id),
                "rzp_payment_id": refund.rzp_payment_id,
                "rzp_refund_id": refund.rzp_refund_id,
                "refund_status": refund_status,
                "total_order_amount_paise": refund.total_order_amount_paise,
                "refund_amount_paise": refund.refund_amount_paise,
                "failure_reason": refund.failure_reason,
                "created_at": refund.created_at,
                "updated_at": refund.updated_at,
            }
            refunds_by_order_id.setdefault(order_id_key, []).append(refund_details)

        order_with_up = []
        for order in orders:
            product = await Product.get(id=order.productid)
            userdata = await User.get(id=order.userid)
            order_refunds = refunds_by_order_id.get(str(order.id), [])

            order_with_up.append({
                "order_id": order.id,
                "product_name": product.name,
                "product_model": product.model,
                "product_details": product.details,
                "product_color": product.product_color,
                "quantity_ordered": order.ordered_quantity,
                "total_amount": order.totalamount,
                "payment_option": order.paymentoption,
                "rzp_payment_id": order.rzp_payment_id,
                "rzp_order_id": order.rzp_order_id,
                "order_status": order.orderstatus,
                "deliveryaddress": order.deliveryaddress,
                "user_name": userdata.name,
                "user_email": userdata.email,
                "purchase_time": order.created_at,
                "user_phonenumber": userdata.phone_number,
                "reasonforcancel": order.reasonforcancel,
                "otherreasonforcancel": order.otherreasonforcancel,
                "created_at": order.created_at,
                "updated_at": order.updated_at,
                "refunds": order_refunds,
                "refund_count": len(order_refunds),
                "total_refunded_amount_paise": sum(r["refund_amount_paise"] for r in order_refunds if r.get("refund_status") == "processed"),
                "latest_refund_status": order_refunds[0]["refund_status"] if order_refunds else None,
            })
        return order_with_up
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------------------------------------------------------
# 5. USER SPECIFIC PROFILE ORDER HISTORIES
# -----------------------------------------------------------------------------
async def order_history(user_id: str):
    try:
        orders = await Order.filter(userid=user_id)
        order_history_with_products = []

        for order in orders:
            product = await Product.get(id=order.productid)
            order_history_with_products.append({
                "order_id": order.id,
                "product_id": product.id,
                "product_name": product.name,
                "product_model": product.model,
                "product_details": product.details,
                "product_color": product.product_color,
                "quantity_ordered": order.ordered_quantity,
                "total_amount": order.totalamount,
                "payment_option": order.paymentoption,
                "rzp_payment_id": order.rzp_payment_id,
                "rzp_order_id": order.rzp_order_id,
                "order_status": order.orderstatus,
                "deliveryaddress": order.deliveryaddress,
                "purchase_time": order.created_at,
                "user_id": order.userid,
                "rfc": order.reasonforcancel,
                "orfc": order.otherreasonforcancel
            })
        return order_history_with_products
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))