# Payments/Methods.py

import random
import razorpay

from fastapi import HTTPException, status
from tortoise.exceptions import DoesNotExist, IntegrityError
from decouple import config

from .Data_Schemas import (
    PaymentSchema,
    VerifyPaymentSchema,
    TransactionsHistoryUser,
)

from Database_and_ORM.Database_Models import (
    Payments,
    User,
    Product,
    Transactions,
)


# -----------------------------------------
# Razorpay Setup
# -----------------------------------------

razorpaykey = config("RAZOR_PAY_KEY")
razorpaysecret = config("RAZOR_PAY_SECRET")

razorpay_client = razorpay.Client(
    auth=(razorpaykey, razorpaysecret)
)


# -----------------------------------------
# CREATE PAYMENT
# -----------------------------------------

async def razorpayfn(
    payment_schema: PaymentSchema,
):

    userid = payment_schema.user_id
    products = payment_schema.products

    try:

        user_entry = await User.get(
            id=userid
        )

        if not user_entry:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        total_amount = 0
        order_notes = []
        product_prices = {}

        for item in products:

            product = await Product.get(
                id=item.productid
            )

            item_total = (
                product.price
                * item.quantity
            )

            total_amount += item_total

            product_prices[
                item.productid
            ] = product.price

            order_notes.append(
                {
                    "productid":
                    item.productid,

                    "quantity":
                    item.quantity,

                    "price_per_unit":
                    product.price,
                }
            )

        order_data = {
            "amount":
            int(total_amount * 100),

            "currency":
            "INR",

            "receipt":
            f"receipt_{random.randint(1000,9999)}",

            "notes":
            {
                "orders":
                order_notes
            },
        }

        order = (
            razorpay_client
            .order
            .create(
                data=order_data
            )
        )

        for item in products:

            await Payments.create(
                userid=userid,

                productid=item.productid,

                price=(
                    product_prices[
                        item.productid
                    ]
                    * item.quantity
                ),

                currency=order[
                    "currency"
                ],

                paymentid=order[
                    "id"
                ],

                paymentstatus=order[
                    "status"
                ],

                receipt=order[
                    "receipt"
                ],

                notes=order[
                    "notes"
                ],
            )

        return {
            "message":
            "Payment initiated successfully",

            "order_id":
            order["id"],

            "amount":
            total_amount,
        }

    except DoesNotExist:

        raise HTTPException(
            status_code=404,
            detail="User/Product not found",
        )

    except IntegrityError:

        raise HTTPException(
            status_code=400,
            detail="Database integrity error",
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


# -----------------------------------------
# VERIFY PAYMENT
# -----------------------------------------

async def verifypayment(
    payload: dict,
    verify_payment:
    VerifyPaymentSchema,
):

    try:

        razorpay_client.utility.verify_payment_signature(
            {
                "razorpay_order_id":
                verify_payment.razorpay_order_id,

                "razorpay_payment_id":
                verify_payment.razorpay_payment_id,

                "razorpay_signature":
                verify_payment.razorpay_signature,
            }
        )

        payment = (
            await Payments
            .filter(
                paymentid=
                verify_payment
                .razorpay_order_id
            )
            .first()
        )

        if not payment:

            raise HTTPException(
                status_code=404,
                detail="Payment not found",
            )

        payment.paymentstatus = "paid"

        payment.paymentid = (
            verify_payment
            .razorpay_payment_id
        )

        await payment.save()

        return {
            "message":
            "Payment verified",

            "payment_id":
            payment.paymentid,
        }

    except razorpay.errors.SignatureVerificationError:

        raise HTTPException(
            status_code=400,
            detail="Invalid signature",
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


# -----------------------------------------
# TRANSACTION HISTORY
# -----------------------------------------

async def transaction_history(
    payload: dict,
    management_data:
    TransactionsHistoryUser,
):

    userid = (
        management_data
        .user_id
    )

    try:

        rows = (
            await Transactions
            .filter(
                userid=userid
            )
            .all()
        )

        history = []

        for row in rows:

            user = await User.get(
                id=row.userid
            )

            history.append(
                {
                    "id":
                    row.id,

                    "paymentid":
                    row.razorpaypaymentid,

                    "price":
                    row.price,

                    "userid":
                    row.userid,

                    "fullname":
                    user.name,
                }
            )

        return history

    except Exception as e:

        raise HTTPException(
            status_code=
            status.HTTP_500_INTERNAL_SERVER_ERROR,

            detail=
            f"Failed: {str(e)}",
        )