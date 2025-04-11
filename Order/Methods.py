import uuid
from fastapi import HTTPException, status, File, UploadFile
from tortoise.exceptions import DoesNotExist, IntegrityError
import re
import os
import shutil
from decouple import config
from .Data_Schemas import OrderSchema,OrderDupSchema
from Database_and_ORM.Database_Models import Order, Cart, Product


async def order_create(payload: dict, order_data: OrderDupSchema):
    user_id = order_data.userid
    cart_id = order_data.cartid
    delivery_address = order_data.deliveryaddress

    # Validate that both user ID and cart ID exist in the Cart table.
    cart_items = await Cart.filter(userid=user_id).all()
    if not cart_items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found for the given user."
        )

    # Optionally, you might want to wrap this in a DB transaction to ensure atomicity.
    created_orders = []
    try:
        # Loop over each cart item to create order entries.
        for item in cart_items:
            # Compute total amount (or use logic you need).
            total_amount = item.price * item.quantity

            # The paymentoption and orderstatus fields are not in the Cart.
            # They can be obtained from the payload if available or set to default values.
            payment_option = payload.get('paymentoption', 'Default Payment Option')
            order_status = payload.get('orderstatus', 'Processing')

            new_order = await Order.create(
                id=uuid.uuid4(),
                userid=user_id,
                productid=item.productid,
                ordered_quantity=item.quantity,  # from Cart.quantity
                totalamount=str(total_amount),    # if Order.totalamount is a CharField, convert as needed
                paymentoption=payment_option,
                orderstatus=order_status,
                deliveryaddress=delivery_address
            )
            created_orders.append(new_order)

        # After successfully creating orders, clear the cart items for that user and cart.
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
                "deliveryaddress": order.deliveryaddress
            }

            order_history_with_products.append(order_details)

        return order_history_with_products

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch order history: {str(e)}",
        )
