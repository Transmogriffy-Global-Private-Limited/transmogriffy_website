import uuid
from fastapi import HTTPException, status, File, UploadFile
from tortoise.exceptions import DoesNotExist, IntegrityError
import re
import os
import shutil
from decouple import config
from .Data_Schemas import OrderSchema,OrderDupSchema,OrderStatusSchema
from Database_and_ORM.Database_Models import Order, Cart, Product

async def order_create(payload: dict, order_data: OrderDupSchema):
    user_id = order_data.user_id
    delivery_address = order_data.deliveryaddress

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
            total_amount = item.price * item.quantity
            payment_option = payload.get('paymentoption')
            order_status = payload.get('orderstatus', 'Processing')

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
                "quantity_ordered": order.ordered_quantity,
                "total_amount": order.totalamount,
                "payment_option": order.paymentoption,
                "order_status": order.orderstatus,
                "deliveryaddress": order.deliveryaddress,
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
