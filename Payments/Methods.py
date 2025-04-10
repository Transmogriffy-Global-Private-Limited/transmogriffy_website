import uuid
from fastapi import HTTPException, status, File, UploadFile
from tortoise.exceptions import DoesNotExist, IntegrityError
import re
import os
import shutil
import razorpay
from decouple import config
from .Data_Schemas import PaymentSchema, Transactions, TransactionsHistoryUser
from Database_and_ORM.Database_Models import (
    Payments,
    User,
    Product,
    Transactions,
)
import razorpay
import random
from decouple import config

razorpaykey = config("RAZOR_PAY_KEY")
razorpaysecret = config("RAZOR_PAY_SECRET")


razorpay_client = razorpay.Client(auth=(razorpaykey, razorpaysecret))

async def razorpayfn(payload: dict, payment_schema: PaymentSchema):

    userid = payment_schema.user_id
    print(userid)
    productid = payment_schema.productid
    print(productid)
    price = payment_schema.price

    try:

        user_entry = await User.get(id=userid)
        if not user_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User entry not found",
            )

        product_entry = await Product.get(id=productid)
        if not product_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product entry not found",
            )
        order_data = {
            "amount": int(price) * 100,
            "currency": "INR",
            "receipt": f"receipt_{random.randint(1000,9999)}",
            "notes": {"message": "data processing done"},
        }

        order = razorpay_client.order.create(data=order_data)
        print(order)
        payment_data = {
            "userid": userid,
            "productid": productid,
            "order_id": order["id"],
            "price": order["amount"],
            "currency": order["currency"],
            "paymentid":order["id"],
            "status": order["status"],
            "receipt": order["receipt"],
            "notes": order["notes"],
        }

        new_order = await Payments.create(**payment_data)

        return {
            "message": "Payment processed successfully",
            "order_id": order["id"],
        }

    except DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Either user or product does not exist",
        )
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database integrity error. Please check your data.",
        )
    except Exception as e:
        print(f"An error occurred: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred. Please try again later.",
        )
async def verifypayment(payload: dict, verify_payment: Transactions):
    userid = verify_payment.user_id
    productid = verify_payment.productid
    razorpaypamentid = verify_payment.razorpaypaymentid
    price = verify_payment.price
    try:
        payment_verification = await Transactions.create(
            id=uuid.uuid4,
            userid=userid,
            productid=productid,
            razorpaypamentid=razorpaypamentid,
            price=price,
        )
        return payment_verification
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error occurred: {str(e)}",
        )


async def transaction_history(
    payload: dict, management_data: TransactionsHistoryUser
):
    userid = management_data.user_id
    try:
        thus = await Transactions.get(userid=userid)
        transactionshistory = []
        for thu in thus:
            userdetails = await User.get(id=thu.userid)
            order_details = {
                "id": thu.id,
                "paymentid": thu.razorpaypaymentid,
                "price": thu.price,
                "userid": thu.userid,
                "fullname": thu.name,
            }
            transactionshistory.append(order_details)
        return transactionshistory
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch transaction history: {str(e)}",
        )
