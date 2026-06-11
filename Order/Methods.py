import uuid
from fastapi import HTTPException, status, File, UploadFile
from tortoise.exceptions import DoesNotExist, IntegrityError
import re
import os
import shutil
from decouple import config
from .Data_Schemas import OrderSchema,OrderDupSchema,OrderStatusSchema
from Database_and_ORM.Database_Models import Order, Cart, Product, User, Admin, Refund_Instances
from Comms.Methods import send_templated_email
from fastapi import HTTPException, status
from tortoise.exceptions import DoesNotExist
from razorpay_refunds.methods.initiate_refund import initiate_refund

# async def order_create(payload: dict, order_data: OrderDupSchema):
#     user_id = order_data.user_id
#     delivery_address = order_data.deliveryaddress
#     payment_option = order_data.paymentoption
#     order_status = order_data.orderstatus

#     cart_items = await Cart.filter(userid=user_id).all()
#     print("Cart items:", cart_items)
#     print(len(cart_items))
#     if len(cart_items) == 0:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Cart not found for the given user."
#             )
#     created_orders = []
#     try:
       

#         for item in cart_items:
#             total_amount = item.price
         

#             # Create a new order for each cart item.
#             new_order = await Order.create(
#                 id=uuid.uuid4(),
#                 userid=user_id,
#                 productid=item.productid,
#                 ordered_quantity=item.quantity,
#                 totalamount=str(total_amount),
#                 paymentoption=payment_option,
#                 orderstatus=order_status,
#                 deliveryaddress=delivery_address
#             )
#             created_orders.append(new_order)
#         await Cart.filter(userid=user_id).delete()

#                 # ---- MAIL: order created (single mail, summary of all items) ----
#         try:
#             from Comms.Methods import send_templated_email  # uses Comms email infra
#             user = await User.get(id=user_id)

#             # Build a compact summary (one line per order)
#             summary_lines = []
#             for o in created_orders:
#                 p = await Product.get(id=o.productid)
#                 summary_lines.append(
#                     f"- Order ID: {o.id} | {p.name} ({p.model}) | Qty: {o.ordered_quantity} | Amount: {o.totalamount} | Status: {o.orderstatus}"
#                 )
#             orders_summary = "\n".join(summary_lines)

#             await send_templated_email(
#                 to_email=user.email,
#                 template_name="order_created",
#                 username=user.name,
#                 orders_summary=orders_summary,
#                 delivery_address=delivery_address,
#                 payment_option=payment_option,
#             )
#         except Exception as _mail_err:
#             # Don't break order creation if mail fails
#             pass

#         return {"message": "Order created successfully.", "orders": created_orders}

#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to create order: {str(e)}"
#         )


async def order_create(
    payload: dict,
    order_data
):

    try:

        # -------------------------
        # VALIDATE INPUT
        # -------------------------
        if not order_data.user_id:
            raise HTTPException(
                status_code=400,
                detail="user_id is required"
            )

        if not order_data.rzp_order_id:
            raise HTTPException(
                status_code=400,
                detail="rzp_order_id is required"
            )

        if not order_data.rzp_payment_id:
            raise HTTPException(
                status_code=400,
                detail="rzp_payment_id is required"
            )

        # -------------------------
        # VERIFY USER
        # -------------------------
        user = await User.get(
            id=order_data.user_id
        )

        # -------------------------
        # LOAD CART
        # -------------------------
        cart_items = await Cart.filter(
            userid=order_data.user_id
        ).all()

        if not cart_items:

            raise HTTPException(
                status_code=404,
                detail="Cart is empty"
            )

        created_orders = []

        # -------------------------
        # TRANSACTION
        # -------------------------
        async with in_transaction():

            for item in cart_items:

                product = await Product.get(
                    id=item.productid
                )

                quantity = int(
                    item.quantity
                )

                # -------------------------
                # STOCK VALIDATION
                # -------------------------
                if (
                    product.quantity
                    <
                    quantity
                ):

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Insufficient stock "
                            f"for product "
                            f"{product.name}"
                        )
                    )

                total_amount = (
                    float(
                        product.price
                    )
                    *
                    quantity
                )

                # -------------------------
                # CREATE ORDER
                # -------------------------
                order = await Order.create(

                    id=uuid.uuid4(),

                    userid=order_data.user_id,

                    productid=item.productid,

                    ordered_quantity=quantity,

                    totalamount=str(
                        total_amount
                    ),

                    paymentoption=
                    order_data.paymentoption,

                    deliveryaddress=
                    order_data.deliveryaddress,

                    # safer until payment verification
                    orderstatus=
                    "payment_received",

                    rzp_order_id=
                    order_data.rzp_order_id,

                    rzp_payment_id=
                    order_data.rzp_payment_id
                )

                created_orders.append(
                    order
                )

                # -------------------------
                # REDUCE STOCK
                # -------------------------
                await Product.filter(
                    id=product.id
                ).update(

                    quantity=(
                        product.quantity
                        -
                        quantity
                    )
                )

            # -------------------------
            # CLEAR CART
            # -------------------------
            await Cart.filter(
                userid=order_data.user_id
            ).delete()

        # -------------------------
        # RESPONSE
        # -------------------------
        return {

            "message":
            "Order created successfully",

            "user_id":
            str(user.id),

            "total_orders":
            len(
                created_orders
            ),

            "orders": [

                {

                    "order_id":
                    str(
                        order.id
                    ),

                    "product_id":
                    str(
                        order.productid
                    ),

                    "amount":
                    order.totalamount,

                    "status":
                    order.orderstatus
                }

                for order
                in created_orders
            ]
        }

    except DoesNotExist:

        raise HTTPException(
            status_code=404,
            detail=(
                "User/Product "
                "not found"
            )
        )

    except IntegrityError:

        raise HTTPException(
            status_code=400,
            detail=(
                "Database "
                "integrity error"
            )
        )

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Order creation failed: "
                f"{str(e)}"
            )
        )



async def get_allorders():
    try:
        orders = await Order.all()

        # Fetch all refund rows once, then group by order_id.
        # This avoids one refund query per order.
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

                # Refund details for this order.
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


async def order_history(user_id: str):

    try:

        orders = await Order.filter(userid=user_id)
        
        order_history_with_products = []

        for order in orders:
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
                "user_id": order.userid,
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
    

# async def order_status_update(order_status: OrderStatusSchema):
#     try:
#         # Validate both orderid and orderstatus are provided
#         if not order_status.orderid or not order_status.orderstatus:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Both 'orderid' and 'orderstatus' must be provided."
#             )

#         # Fetch the order
#         order = await Order.get(id=order_status.orderid)
#         if not order:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail=f"Order with ID {order_status.orderid} not found."
#             )

#         # Update status and save
#         order.orderstatus = order_status.orderstatus
#         await order.save()

#         return {"message": f"Order status updated to '{order_status.orderstatus}' successfully."}

#     except DoesNotExist:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Order with ID {order_status.orderid} does not exist."
#         )
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to update order status: {str(e)}"
#         )
async def order_status_update(order_status: OrderStatusSchema):
    try:

        # -------------------------
        # VALIDATE INPUT
        # -------------------------
        if not order_status.orderid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="orderid is required."
            )

        if not order_status.orderstatus:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="orderstatus is required."
            )

        # -------------------------
        # STATE TRANSITION RULES
        # -------------------------
        ALLOWED_TRANSITIONS = {

            "payment_pending": [
                "paid",
                "cancelled"
            ],

            "paid": [
                "processing",
                "refund_pending"
            ],

            "processing": [
                "shipped",
                "cancelled"

            ],

            "shipped": [
                "delivered"
            ],

            "refund_pending": [
                "refunded"
            ]
        }

        # -------------------------
        # LOAD ORDER
        # -------------------------
        order = await Order.get(
            id=order_status.orderid
        )

        current_status = (
            str(order.orderstatus).lower()
            if order.orderstatus
            else "payment_pending"
        )

        requested_status = (
            str(order_status.orderstatus)
            .lower()
        )

        # -------------------------
        # PREVENT INVALID MOVES
        # -------------------------
        allowed_next = (
            ALLOWED_TRANSITIONS
            .get(current_status, [])
        )

        if requested_status not in allowed_next:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Invalid status transition. "
                    f"Cannot move "
                    f"'{current_status}' "
                    f"→ "
                    f"'{requested_status}'"
                )
            )

        # -------------------------
        # SAVE STATUS
        # -------------------------
        old_status = order.orderstatus

        order.orderstatus = requested_status

        await order.save()

        # -------------------------
        # SEND EMAIL
        # -------------------------
        try:

            userdata = await User.get(
                id=order.userid
            )

            product = await Product.get(
                id=order.productid
            )

            await send_templated_email(
                to_email=userdata.email,
                template_name="updatedorder",

                username=userdata.name,

                order_id=str(order.id),

                old_status=str(old_status),

                new_status=str(
                    order.orderstatus
                ),

                product_name=product.name,

                product_model=product.model,

                quantity=str(
                    order.ordered_quantity
                )
            )

        except Exception as mail_err:

            print(
                "Order status email failed:",
                str(mail_err)
            )

        return {
            "message":
            "Order status updated successfully",

            "order_id":
            str(order.id),

            "old_status":
            old_status,

            "new_status":
            order.orderstatus
        }

    except DoesNotExist:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Order "
                f"{order_status.orderid} "
                f"not found"
            )
        )

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to update "
                f"order status: "
                f"{str(e)}"
            )
        )




# async def cancel_order(order_id: str, reasonforcancel: str, otherreasonforcancel: str):
#     try:
#         # Validate reason
#         if not reasonforcancel or reasonforcancel == "":
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Cancellation reason must be provided."
#             )

#         # Check if 'other' is selected and validate otherreasonforcancel
#         if reasonforcancel == "other":
#             if not otherreasonforcancel or otherreasonforcancel == "":
#                 raise HTTPException(
#                     status_code=status.HTTP_400_BAD_REQUEST,
#                     detail="Please specify the cancellation reason in 'otherreasonforcancel'."
#                 )
#             final_reason = "other"
#             other_reason_value = otherreasonforcancel
#         else:
#             final_reason = reasonforcancel
#             other_reason_value = None

#         # Fetch the order
#         order = await Order.get(id=order_id)
#         if not order:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail=f"Order with ID {order_id} not found."
#             )

#         # Check if already canceled
#         if order.orderstatus == "canceled":
#             return {
#                 "message": f"Order {order.id} has already been canceled.",
#                 "existing_cancellation_reason": order.reasonforcancel,
#                 "custom_reason": order.otherreasonforcancel
#             }

#         # Only allow cancellation if status is pending or null/empty
#         if order.orderstatus not in ["", "none", "null", "pending"]:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail=f"Order {order.id} cannot be canceled because its status is '{order.orderstatus}'. Only 'pending' or null status orders can be canceled."
#             )

#         # Update order status and reason
#         order.orderstatus = "canceled"
#         order.reasonforcancel = final_reason
#         order.otherreasonforcancel = other_reason_value
#         await order.save()

#         # Restock product
#         product = await Product.get(id=order.productid)
#         updated_quantity = product.quantity + int(order.ordered_quantity)
#         await Product.filter(id=order.productid).update(quantity=updated_quantity)

#         return {
#             "message": f"Order {order.id} canceled successfully. {order.ordered_quantity} units restocked.",
#             "cancellation_reason": final_reason,
#             "custom_reason": other_reason_value
#         }

#     except DoesNotExist:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Order or product not found."
#         )
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to cancel order: {str(e)}"
#         )


async def cancel_order(
    order_id: str,
    reasonforcancel: str,
    otherreasonforcancel: str
):

    try:

        # -------------------------
        # VALIDATE INPUT
        # -------------------------
        if not reasonforcancel:
            raise HTTPException(
                status_code=400,
                detail="Cancellation reason required."
            )

        final_reason = reasonforcancel
        custom_reason = None

        if (
            str(reasonforcancel)
            .lower()
            == "other"
        ):

            if not otherreasonforcancel:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Please provide "
                        "otherreasonforcancel"
                    )
                )

            custom_reason = (
                otherreasonforcancel
            )

        # -------------------------
        # LOAD ORDER
        # -------------------------
        order = await Order.get(
            id=order_id
        )

        current_status = (
            str(order.orderstatus)
            .lower()
            if order.orderstatus
            else "payment_pending"
        )

        # -------------------------
        # PREVENT DUPLICATE CANCEL
        # -------------------------
        if current_status in [
            "cancelled",
            "canceled"
        ]:

            return {
                "message":
                "Order already cancelled",

                "order_id":
                str(order.id),

                "reason":
                order.reasonforcancel
            }

        # -------------------------
        # ALLOWED CANCELLATION
        # -------------------------
        CANCELLABLE = [
            "payment_pending",
            "paid",
            "processing"
        ]

        if current_status not in CANCELLABLE:

            raise HTTPException(
                status_code=400,
                detail=(
                    f"Order cannot "
                    f"be cancelled "
                    f"from status "
                    f"'{current_status}'"
                )
            )

        # -------------------------
        # UPDATE ORDER
        # -------------------------
        order.orderstatus = (
            "cancelled"
        )

        order.reasonforcancel = (
            final_reason
        )

        order.otherreasonforcancel = (
            custom_reason
        )

        await order.save()

        # -------------------------
        # RESTOCK PRODUCT
        # -------------------------
        product = await Product.get(
            id=order.productid
        )

        await Product.filter(
            id=order.productid
        ).update(

            quantity=(
                product.quantity
                +
                int(
                    order.ordered_quantity
                )
            )
        )

        # -------------------------
        # AUTO REFUND
        # -------------------------
        refund_result = None

        if current_status in [
            "paid",
            "processing"
        ]:

            try:

                refund_result = (
                    await initiate_refund(
                        order_id
                    )
                )

                print(
                    "Refund success:",
                    refund_result
                )

            except Exception as e:

                print(
                    "Refund failed:",
                    str(e)
                )

        # -------------------------
        # EMAIL
        # -------------------------
        try:

            user = await User.get(
                id=order.userid
            )

            reason_text = (
                final_reason
            )

            if custom_reason:

                reason_text += (
                    f"\n"
                    f"{custom_reason}"
                )

            await send_templated_email(

                to_email=user.email,

                template_name=
                "canceledorder",

                username=user.name,

                order_id=
                str(order.id),

                product_name=
                product.name,

                product_model=
                product.model,

                quantity=
                str(
                    order.ordered_quantity
                ),

                reason=reason_text
            )

        except Exception as mail_err:

            print(
                "Mail failed:",
                str(mail_err)
            )

        return {

            "message":
            "Order cancelled successfully",

            "order_id":
            str(order.id),

            "status":
            order.orderstatus,

            "refund":
            (
                "initiated"
                if refund_result
                else "not_required"
            ),

            "reason":
            final_reason,

            "custom_reason":
            custom_reason
        }

    except DoesNotExist:

        raise HTTPException(
            status_code=404,
            detail=(
                "Order/Product "
                "not found"
            )
        )

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Cancel failed: "
                f"{str(e)}"
            )
        )
