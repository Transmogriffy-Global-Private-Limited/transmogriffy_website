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


async def order_create(payload: dict, order_data: OrderDupSchema):
    user_id = order_data.user_id
    delivery_address = order_data.deliveryaddress
    payment_option = order_data.paymentoption
    order_status = order_data.orderstatus

    cart_items = await Cart.filter(userid=user_id).all()
    print("Cart items:", cart_items)
    print(len(cart_items))

    if len(cart_items) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found for the given user."
        )

    created_orders = []
    try:
        for item in cart_items:
            total_amount = item.price

            # Create a new order for each cart item.
            new_order = await Order.create(
                id=uuid.uuid4(),
                userid=user_id,
                productid=item.productid,
                ordered_quantity=item.quantity,
                totalamount=str(total_amount),
                paymentoption=payment_option,
                rzp_payment_id = order_data.rzp_payment_id,
                rzp_order_id = order_data.rzp_order_id,
                orderstatus=order_status,
                deliveryaddress=delivery_address
            )
            created_orders.append(new_order)

        # clear cart
        await Cart.filter(userid=user_id).delete()

        # -------------------------
        # EMAIL: order created (USER + ALL ADMINS) ✅
        # one email per checkout, summarizing all created orders
        # -------------------------
        try:
            userdata = await User.get(id=user_id)

            order_ids_text = "\n".join([str(o.id) for o in created_orders])

            # Build a readable summary
            summary_lines = []
            total_sum = 0.0
            for o in created_orders:
                product = await Product.get(id=o.productid)
                qty = int(o.ordered_quantity) if str(o.ordered_quantity).isdigit() else o.ordered_quantity
                line = f"- {product.name} ({product.model}) | Qty: {qty} | Amount: {o.totalamount}"
                summary_lines.append(line)

                try:
                    total_sum += float(o.totalamount)
                except Exception:
                    pass

            order_summary = "\n".join(summary_lines)
            total_amount_text = str(total_sum) if total_sum > 0 else "N/A"

            # ✅ Mail the customer
            await send_templated_email(
                to_email=userdata.email,
                template_name="ordercreated",
                username=userdata.name,
                order_summary=order_summary,
                payment_option=payment_option,
                delivery_address=delivery_address,
            )

            # ✅ Mail each admin from DB
            admins = await Admin.all()
            for admin in admins:
                # (optional guard) skip empty emails if ever present
                if not getattr(admin, "email", None):
                    continue

                await send_templated_email(
                    to_email=admin.email,
                    template_name="adordercreated",
                    customer_name=userdata.name,
                    customer_email=userdata.email,
                    order_ids=order_ids_text,
                    order_summary=order_summary,
                    payment_option=payment_option,
                    delivery_address=delivery_address,
                    total_amount=total_amount_text
                )

        except Exception as mail_err:
            import traceback
            print("Order created email failed (mail block) ✅ FULL TRACE:")
            traceback.print_exc()

        return {"message": "Order created successfully.", "orders": created_orders}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create order: {str(e)}"
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
        # Validate both orderid and orderstatus are provided
        if not order_status.orderid or not order_status.orderstatus:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Both 'orderid' and 'orderstatus' must be provided."
            )

        # Fetch the order
        order = await Order.get(id=order_status.orderid)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order with ID {order_status.orderid} not found."
            )

        # Update status and save
        oldstatus = order.orderstatus
        order.orderstatus = order_status.orderstatus
        await order.save()

        # -------------------------
        # EMAIL: order status updated (NEW)
        # -------------------------
        try:
            userdata = await User.get(id=order.userid)
            product = await Product.get(id=order.productid)

            extra_info = ""
            # If you later represent deletions as a status like "deleted", we include it here too.
            if str(order.orderstatus).lower() in ["canceled", "cancelled"]:
                extra_info = "This order has been canceled."
            elif str(order.orderstatus).lower() in ["deleted", "removed"]:
                extra_info = "This order has been deleted/removed."

            await send_templated_email(
                to_email=userdata.email,
                template_name="updatedorder",
                username=userdata.name,
                order_id=str(order.id),
                new_status=str(order.orderstatus),
                old_status = str(oldstatus),
                product_name=product.name,
                product_model=product.model,
                quantity=str(order.ordered_quantity)
            )
        except Exception as mail_err:
            print(f"Order status update email failed: {mail_err}")

        return {"message": f"Order status updated to '{order_status.orderstatus}' successfully."}

    except DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with ID {order_status.orderid} does not exist."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update order status: {str(e)}"
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


async def cancel_order(order_id: str, reasonforcancel: str, otherreasonforcancel: str):
    try:
        # Validate reason
        if not reasonforcancel or reasonforcancel == "":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cancellation reason must be provided."
            )

        # Check if 'other' is selected and validate otherreasonforcancel
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

        # Fetch the order
        order = await Order.get(id=order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order with ID {order_id} not found."
            )

        # Check if already canceled
        if order.orderstatus == "canceled":
            return {
                "message": f"Order {order.id} has already been canceled.",
                "existing_cancellation_reason": order.reasonforcancel,
                "custom_reason": order.otherreasonforcancel
            }

        # Only allow cancellation if status is pending or null/empty
        if order.orderstatus not in ["", "none", "null", "pending"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Order {order.id} cannot be canceled because its status is '{order.orderstatus}'. Only 'pending' or null status orders can be canceled."
            )

        # Update order status and reason
        order.orderstatus = "canceled"
        order.reasonforcancel = final_reason
        order.otherreasonforcancel = other_reason_value
        await order.save()

        # Restock product
        product = await Product.get(id=order.productid)
        updated_quantity = product.quantity + int(order.ordered_quantity)
        await Product.filter(id=order.productid).update(quantity=updated_quantity)

        try:
            refund_details = await initiate_refund (order_id)
            print(f"Refund successfully initiated. Details: \n {refund_details}")
        except Exception as refund_error:
            print (f"Couldn't automatically process refund. Error: \n{refund_error}")
            pass

        # -------------------------
        # EMAIL: cancellation is also a status update (NEW)
        # -------------------------
        try:
            userdata = await User.get(id=order.userid)

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
            "message": f"Order {order.id} canceled successfully. {order.ordered_quantity} units restocked.",
            "cancellation_reason": final_reason,
            "custom_reason": other_reason_value
        }

    except DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order or product not found."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel order: {str(e)}"
        )