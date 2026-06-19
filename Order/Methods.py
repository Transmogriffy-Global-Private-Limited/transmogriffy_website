import uuid
import logging
import random
import re
import os
import shutil
import razorpay
from decouple import config
from fastapi import HTTPException, status, File, UploadFile
from tortoise.exceptions import DoesNotExist, IntegrityError
from tortoise.transactions import in_transaction
import logging
# Schema and Model mappings
from .Data_Schemas import OrderSchema, OrderDupSchema, OrderStatusSchema, CheckoutSchema
from Database_and_ORM.Database_Models import Order, Cart, Product, User, Admin, Refund_Instances,Payments

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

        user = await User.get(
            id=order_data.user_id
        )

        cart_items = (
            await Cart.filter(
                userid=order_data.user_id
            )
            .all()
        )

        if not cart_items:

            raise HTTPException(
                status_code=404,
                detail="Cart empty"
            )

        total_amount = 0
        manifest = []

        async with in_transaction() as conn:

            for item in cart_items:

                product = (
                    await Product
                    .get(
                        id=item.productid
                    )
                    .using_db(conn)
                )

                reserved = await (
                    Payments
                    .filter(
                        productid=str(
                            product.id
                        ),
                        paymentstatus="reserved"
                    )
                    .count()
                )

                available = (
                    product.quantity
                    - reserved
                )

                if available < int(item.quantity):

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"{product.name} "
                            "temporarily unavailable"
                        )
                    )

                total = (
                    float(
                        product.price
                    )
                    * int(
                        item.quantity
                    )
                )

                total_amount += total

                manifest.append(
                    {
                        "product_id":
                        str(
                            product.id
                        ),

                        "quantity":
                        int(
                            item.quantity
                        ),

                        "price":
                        total
                    }
                )

            rzp_order = (
                razorpay_client
                .order
                .create(
                    {
                        "amount":
                        int(
                            total_amount
                            * 100
                        ),

                        "currency":
                        "INR",

                        "receipt":
                        (
                            f"rcpt_"
                            f"{random.randint(1000,9999)}"
                        )
                    }
                )
            )

            created = []

            for row in manifest:

                order = (
                    await Order.create(

                        id=uuid.uuid4(),

                        userid=str(
                            user.id
                        ),

                        productid=row[
                            "product_id"
                        ],

                        ordered_quantity=str(
                            row[
                                "quantity"
                            ]
                        ),

                        totalamount=str(
                            row[
                                "price"
                            ]
                        ),

                        paymentoption=(
                            order_data
                            .paymentoption
                        ),

                        deliveryaddress=(
                            order_data
                            .deliveryaddress
                        ),

                        orderstatus=(
                            "payment_pending"
                        ),

                        rzp_order_id=(
                            rzp_order["id"]
                        ),

                        rzp_payment_id="none",

                        using_db=conn
                    )
                )

                created.append(
                    order
                )

            # DO NOT DELETE CART HERE

        return {

            "message":
            (
                "Order created. "
                "Payment valid for 5 minutes."
            ),

            "order_id":
            rzp_order["id"],

            "amount":
            total_amount,

            "expires_in_seconds":
            300,

            "orders":
            [
                str(x.id)
                for x
                in created
            ]
        }

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# -----------------------------------------------------------------------------
# 2. UPDATE ORDER STATUS (Guarded Transitions)
# -----------------------------------------------------------------------------
async def order_status_update(order_status: OrderStatusSchema):
    try:
        if not order_status.orderid or not order_status.orderstatus:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Both 'orderid' and 'orderstatus' must be provided."
            )

        order = await Order.get(id=order_status.orderid)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order with ID {order_status.orderid} not found."
            )

        ALLOWED_TRANSITIONS = {
            "payment_pending": ["paid", "cancelled", "canceled"],
            "paid": ["processing", "refund_pending"],
            "processing": ["shipped", "cancelled", "canceled"],
            "shipped": ["delivered"],
            "refund_pending": ["refunded"]
        }

        current_status = str(order.orderstatus).lower() if order.orderstatus else "payment_pending"
        requested_status = str(order_status.orderstatus).lower()

        if requested_status not in ALLOWED_TRANSITIONS.get(current_status, []):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Protected lifecycle transition error. Cannot process state mutation '{current_status}' → '{requested_status}'."
            )

        oldstatus = order.orderstatus
        order.orderstatus = order_status.orderstatus
        await order.save()

        try:
            # ✅ FIXED: Read references using legacy model keys 'userid' and 'productid'
            userdata = await User.get(id=order.userid)
            product = await Product.get(id=order.productid)

            await send_templated_email(
                to_email=userdata.email,
                template_name="updatedorder",
                username=userdata.name,
                order_id=str(order.id),
                new_status=str(order.orderstatus),
                old_status=str(oldstatus),
                product_name=product.name,
                product_model=product.model,
                quantity=str(order.ordered_quantity)
            )
        except Exception as mail_err:
            logger.warning(f"Order status update email failed: {mail_err}")

        return {"message": f"Order status updated to '{order_status.orderstatus}' successfully."}

    except DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with ID {order_status.orderid} does not exist."
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update order status: {str(e)}"
        )


# -----------------------------------------------------------------------------
# 3. CANCEL ORDER & REVERT TRANSACTION LIFECYCLES
# -----------------------------------------------------------------------------
async def cancel_order(order_id: str, reasonforcancel: str, otherreasonforcancel: str):
    try:
        if not reasonforcancel or reasonforcancel == "":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cancellation reason must be provided."
            )

        if reasonforcancel == "other":
            if not otherreasonforcancel or otherreasonforcancel == "":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Please specify the cancellation reason in 'otherreasonforcancel'."
                )
            final_reason = "other"
            other_reason_value = otherreasonforcancel
        else:
            final_reason = reasonforcancel
            other_reason_value = None

        order = await Order.get(id=order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order with ID {order_id} not found."
            )

        current_status = str(order.orderstatus).lower() if order.orderstatus else "payment_pending"

        if current_status in ["cancelled", "canceled"]:
            return {
                "message": f"Order {order.id} has already been canceled.",
                "existing_cancellation_reason": order.reasonforcancel,
                "custom_reason": order.otherreasonforcancel
            }

        if current_status not in ["", "none", "null", "pending", "payment_pending", "paid", "processing"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Order {order.id} cannot be canceled because its status is '{order.orderstatus}'."
            )

        async with in_transaction() as connection:
            order.orderstatus = "cancelled"
            order.reasonforcancel = final_reason
            order.otherreasonforcancel = other_reason_value
            await order.save(using_db=connection)

            if current_status in ["paid", "processing"]:
                # ✅ FIXED: Changed reference lookup to 'productid'
                product = await Product.get(id=order.productid)
                updated_quantity = product.quantity + int(order.ordered_quantity)
                await Product.filter(id=order.productid).using_db(connection).update(quantity=updated_quantity)

        refund_status = "not_required"
        if current_status in ["paid", "processing"]:
            try:
                refund_details = await initiate_refund(order_id)
                refund_status = "initiated"
            except Exception as refund_error:
                print(f"Couldn't automatically process refund. Error: \n{refund_error}")
                refund_status = "failed_manual_intervention_required"

        try:
            # ✅ FIXED: Changed lookup attributes to use legacy 'userid' and 'productid'
            userdata = await User.get(id=order.userid)
            product = await Product.get(id=order.productid)

            extra_info = f"Cancellation reason: {final_reason}"
            if other_reason_value:
                extra_info += f"\nCustom reason: {other_reason_value}"

            await send_templated_email(
                to_email=userdata.email,
                template_name="canceledorder",
                username=userdata.name,
                order_id=str(order.id),
                product_name=product.name,
                product_model=product.model,
                quantity=str(order.ordered_quantity),
                reason=extra_info
            )
        except Exception as mail_err:
            print(f"Order cancellation email failed: {mail_err}")

        return {
            "message": f"Order {order.id} canceled successfully. Refund status: {refund_status}",
            "cancellation_reason": final_reason,
            "custom_reason": other_reason_value
        }

    except DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order or product record references not found."
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel order: {str(e)}"
        )


# -----------------------------------------------------------------------------
# 4. VIEW ALL ORDERS (Admin Metric Tooling)
# -----------------------------------------------------------------------------
async def get_allorders():
    try:
        orders = await Order.all()
        refund_rows = await Refund_Instances.all()
        refunds_by_order_id = {}

        for refund in refund_rows:
            order_id_key = str(refund.order_id)
            refund_status = refund.refund_status
            if hasattr(refund_status, "value"):
                refund_status = refund_status.value

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
            # ✅ FIXED: Read from legacy model attributes 'productid' and 'userid'
            product = await Product.get(id=order.productid)
            userdata = await User.get(id=order.userid)
            order_refunds = refunds_by_order_id.get(str(order.id), [])

            order_details = {
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
                "address": order.deliveryaddress,
                "user_phonenumber": userdata.phone_number,
                "reasonforcancel": order.reasonforcancel,
                "otherreasonforcancel": order.otherreasonforcancel,
                "created_at": order.created_at,
                "updated_at": order.updated_at,
                "refunds": order_refunds,
                "refund_count": len(order_refunds),
                "total_refunded_amount_paise": sum(
                    refund["refund_amount_paise"]
                    for refund in order_refunds
                    if refund.get("refund_status") == "processed"
                ),
                "latest_refund_status": (
                    order_refunds[0]["refund_status"]
                    if order_refunds
                    else None
                ),
            }
            order_with_up.append(order_details)

        return order_with_up

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch order history: {str(e)}",
        )


# -----------------------------------------------------------------------------
# 5. USER METRIC TIMELINES
# -----------------------------------------------------------------------------
async def order_history(user_id: str):
    try:
        # ✅ FIXED: Swapped lookup criteria keyword straight to legacy field attribute 'userid'
        orders = await Order.filter(userid=user_id).all()
        order_history_with_products = []

        for order in orders:
            # ✅ FIXED: Changed reference lookup parameter to legacy field 'productid'
            product = await Product.get(id=order.productid)
            order_details = {
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
                "user_id": order.userid, # ✅ FIXED: Aligned output dictionary variable mapping to 'userid'
                "rfc": order.reasonforcancel,
                "orfc": order.otherreasonforcancel
            }
            order_history_with_products.append(order_details)

        return order_history_with_products

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch order history: {str(e)}",
        )