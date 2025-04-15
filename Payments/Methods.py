import uuid
from fastapi import HTTPException, status, File, UploadFile
from tortoise.exceptions import DoesNotExist, IntegrityError
import re
import os
import shutil
import razorpay
from decouple import config
from .Data_Schemas import PaymentSchema, TransactionsSchema, TransactionsHistoryUser
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


#example payload
"""
{
  "user_id": "eab6b60f-d123-4a5c-934d-43a9038fa1b1",
  "products": [
    {
      "productid": "f423f50d-cbc4-4a10-86a7-d37b87428e1f",
      "quantity": 2
    },
    {
      "productid": "9b6d0d4e-857a-41f9-9872-b2583429c891",
      "quantity": 1
    }
  ]
}

"""
async def razorpayfn(payment_schema: PaymentSchema):
    userid = payment_schema.user_id
    products = payment_schema.products

    try:
        user_entry = await User.get(id=userid)
        if not user_entry:
            raise HTTPException(status_code=404, detail="User not found")

        total_amount = 0
        order_notes = []
        product_prices = {}

        for item in products:
            product_entry = await Product.get(id=item.productid)
            if not product_entry:
                raise HTTPException(status_code=404, detail=f"Product {item.productid} not found")

            item_total = product_entry.price * item.quantity
            print(item_total)
            total_amount += item_total
            print(total_amount)
            product_prices[item.productid] = product_entry.price

            order_notes.append(
                {
                    "productid": item.productid,
                    "quantity": item.quantity,
                    "price_per_unit": product_entry.price
                }
            )

        order_data = {
            "amount": int(total_amount) * 100,
            "currency": "INR",
            "receipt": f"receipt_{random.randint(1000,9999)}",
            "notes": {"orders": order_notes}
        }

        order = razorpay_client.order.create(data=order_data)
        print("Razorpay order created:", order)

        for item in products:
            await Payments.create(
                userid=userid,
                productid=item.productid,
                order_id=order["id"],
                price=product_prices[item.productid] * item.quantity,
                currency=order["currency"],
                paymentid=order["id"],
                paymentstatus=order["status"],
                receipt=order["receipt"],
                notes=order["notes"]
            )

        return {
            "message": "Payment initiated successfully",
            "order_id": order["id"],
            "amount": total_amount
        }

    except HTTPException as http_exc:
        raise http_exc
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Either user or product does not exist")
    except IntegrityError:
        raise HTTPException(status_code=400, detail="Database integrity error. Please check your data.")
    except Exception as e:
        print(f"An error occurred in razorpayfn: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred. Please try again later.")



async def verifypayment(payload: dict, verify_payment: TransactionsSchema):
    userid = verify_payment.user_id
    razorpaypaymentid = verify_payment.razorpaypaymentid
    products = verify_payment.products

    created_transactions = []

    try:
        for item in products:
            transaction_entry = await Transactions.create(
                id=str(uuid.uuid4()),
                userid=userid,
                productid=item.productid,
                razorpaypaymentid=razorpaypaymentid,
                price=item.price,
            )
            created_transactions.append(transaction_entry)

        return {
            "message": "Payment verification records created successfully.",
            "transactions": created_transactions
        }

    except Exception as e:
        print(f"Error in verifypayment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error occurred: {str(e)}"
        )




# async def transaction_history(
#     payload: dict, management_data: TransactionsHistoryUser
# ):
#     userid = management_data.user_id
#     try:
#         thus = await Transactions.get(userid=userid)
#         transactionshistory = []
#         for thu in thus:
#             userdetails = await User.get(id=thu.userid)
#             order_details = {
#                 "id": thu.id,
#                 "paymentid": thu.razorpaypaymentid,
#                 "price": thu.price,
#                 "userid": thu.userid,
#                 "fullname": thu.name,
#             }
#             transactionshistory.append(order_details)
#         return transactionshistory
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to fetch transaction history: {str(e)}",
#         )


async def transaction_history(
    payload: dict, management_data: TransactionsHistoryUser
):
    userid = management_data.user_id
    try:
        thus = await Transactions.filter(userid=userid).all()  # ← fixed this
        transactionshistory = []

        for thu in thus:
            userdetails = await User.get(id=thu.userid)
            order_details = {
                "id": thu.id,
                "paymentid": thu.razorpaypaymentid,
                "price": thu.price,
                "userid": thu.userid,
                "fullname": userdetails.name,  # ← use userdetails fetched here
            }
            transactionshistory.append(order_details)

        return transactionshistory

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch transaction history: {str(e)}",
        )
