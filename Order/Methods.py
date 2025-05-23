import uuid
from fastapi import HTTPException, status, File, UploadFile
from tortoise.exceptions import DoesNotExist, IntegrityError
import re
import os
import shutil
from decouple import config
from .Data_Schemas import OrderSchema,OrderDupSchema,OrderStatusSchema
from Database_and_ORM.Database_Models import Order, Cart, Product,User
from fastapi import HTTPException, status
from tortoise.exceptions import DoesNotExist

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
                orderstatus=order_status,
                deliveryaddress=delivery_address
            )
            created_orders.append(new_order)
        await Cart.filter(userid=user_id).delete()

        return {"message": "Order created successfully.", "orders": created_orders}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create order: {str(e)}"
        )



async def get_allorders():
    try:
        orders = await Order.all()
        order_with_up = []

        for order in orders:
            product =  await Product.get(id=order.productid)
            userdata = await User.get(id=order.userid)
            order_details = {
                "order_id":order.id,
                 "product_name": product.name,
                "product_model": product.model,
                "product_details": product.details,
                "product_color": product.product_color,
                "quantity_ordered": order.ordered_quantity,
                "total_amount": order.totalamount,
                "payment_option": order.paymentoption,
                "order_status": order.orderstatus,
                "deliveryaddress": order.deliveryaddress,
                "user_name": userdata.name,
                "user_email":userdata.email,
                "purchase_time": order.created_at,
                "address":order.deliveryaddress,
                "user_phonenumber":userdata.phone_number
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
                "product_name": product.name,
                "product_model": product.model,
                "product_details": product.details,
                "product_color": product.product_color,
                "quantity_ordered": order.ordered_quantity,
                "total_amount": order.totalamount,
                "payment_option": order.paymentoption,
                "order_status": order.orderstatus,
                "deliveryaddress": order.deliveryaddress,
                "purchase_time": order.created_at,
                "user_id": order.userid
            }

            order_history_with_products.append(order_details)

        return order_history_with_products

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch order history: {str(e)}",
        )
    

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
        order.orderstatus = order_status.orderstatus
        await order.save()

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
