import uuid
from fastapi import HTTPException, status, File, UploadFile
from tortoise.exceptions import DoesNotExist, IntegrityError
import re
import os
import shutil
from decouple import config
from .Data_Schemas import OrderSchema
from Database_and_ORM.Database_Models import Order,Cart,Product

async def order_create(payload:dict,order_data:OrderSchema):
    userid = order_data.userid
    productid = order_data.productid
    quantity = order_data.quantity
    totalamount = order_data.totalamount
    paymentoption = order_data.paymentoption
    orderstatus = order_data.orderstatus
    try:
      new_order_entry = await Order.create(
        id = uuid.uuid4(),
        userid = userid,
        productid = productid,
        quantity=quantity,
        totalamount=totalamount,
        paymentoption=paymentoption,
        orderstatus = orderstatus
      )
      return new_order_entry
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create order: {str(e)}",
        )

# async def order_history(payload:str)