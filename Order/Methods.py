import uuid
from fastapi import HTTPException, status, File, UploadFile
from tortoise.exceptions import DoesNotExist, IntegrityError
import re
import os
import shutil
from decouple import config
from .Data_Schemas import OrderSchema
from Database_and_ORM.Database_Models import Order, Cart, Product


async def order_create(payload: dict, order_data: OrderSchema):
    userid = order_data.user_id
    productid = order_data.productid
    order_quantity = order_data.order_quantity
    totalamount = order_data.totalamount
    paymentoption = order_data.paymentoption
    orderstatus = order_data.orderstatus
    try:
        new_order_entry = await Order.create(
            id=uuid.uuid4(),
            userid=userid,
            productid=productid,
            ordered_quantity=order_quantity,
            totalamount=totalamount,
            paymentoption=paymentoption,
            orderstatus=orderstatus,
        )
        return new_order_entry
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create order: {str(e)}",
        )


async def order_history(userid: str):

    try:

        orders = await Order.filter(userid=userid)

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
            }

            order_history_with_products.append(order_details)

        return order_history_with_products

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch order history: {str(e)}",
        )
