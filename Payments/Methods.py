import uuid
import logging
import random
import razorpay

from decouple import config
from fastapi import HTTPException, status
from tortoise.exceptions import DoesNotExist
from tortoise.transactions import in_transaction

from .Data_Schemas import (
    PaymentSchema,
    TransactionsHistoryUser,
    VerifyPaymentSchema,
)

from Database_and_ORM.Database_Models import (
    Payments,
    User,
    Product,
    Transactions,
)

logger = logging.getLogger("Payments.Methods")

razorpay_client = razorpay.Client(
    auth=(
        config("RAZOR_PAY_KEY"),
        config("RAZOR_PAY_SECRET"),
    )
)


# ==================================================
# CREATE PAYMENT
# ==================================================
async def razorpayfn(
    payment_schema: PaymentSchema
):

    try:

        userid = payment_schema.user_id
        products = payment_schema.products

        await User.get(id=userid)

        total_amount = 0
        prices = {}
        order_notes = []

        # -----------------------------
        # Validate Products
        # -----------------------------
        for item in products:

            if not item.productid:
                raise HTTPException(
                    status_code=400,
                    detail="productid required"
                )

            if item.quantity <= 0:
                raise HTTPException(
                    status_code=400,
                    detail="quantity must be greater than 0"
                )

            product = await Product.get(
                id=item.productid
            )

            prices[item.productid] = (
                product.price
            )

            total_amount += (
                product.price
                * item.quantity
            )

            order_notes.append({
                "product_id": str(
                    item.productid
                ),
                "quantity": item.quantity,
                "unit_price": product.price
            })

        # -----------------------------
        # Create Razorpay Order
        # -----------------------------
        order = (
            razorpay_client.order.create(
                {
                    "amount": int(
                        total_amount
                        * 100
                    ),

                    "currency": "INR",

                    "receipt":
                    f"receipt_"
                    f"{random.randint(1000,9999)}",

                    # FIX → REQUIRED
                    "notes": {
                        "products":
                        order_notes
                    }
                }
            )
        )

        # -----------------------------
        # Save Local Payment Rows
        # -----------------------------
        for item in products:

            await Payments.create(

                userid=userid,

                # ForeignKey
                productid=await Product.get(
                    id=item.productid
                ),

                price=(
                    prices[
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

                paymentstatus=(
                    "created"
                ),

                receipt=order[
                    "receipt"
                ],

                # FIX → REQUIRED
                notes=order[
                    "notes"
                ]
            )

        return {

            "message":
            "Payment initiated",

            "order_id":
            order["id"],

            "amount":
            total_amount,
        }

    except DoesNotExist:

        raise HTTPException(
            status_code=404,
            detail="User/Product not found"
        )

    except HTTPException:
        raise

    except Exception as e:

        logger.error(
            f"Create payment failed: {str(e)}"
        )

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

# ==================================================
# VERIFY PAYMENT
# ==================================================
async def verifypayment(
    verify_payment:
    VerifyPaymentSchema
):

    try:

        payment_id = (
            verify_payment
            .razorpay_payment_id
        )

        order_id = (
            verify_payment
            .razorpay_order_id
        )

        signature = (
            verify_payment
            .razorpay_signature
        )

        userid = (
            verify_payment
            .user_id
        )

        razorpay_client.utility.verify_payment_signature(
            {
                "razorpay_order_id":
                order_id,

                "razorpay_payment_id":
                payment_id,

                "razorpay_signature":
                signature,
            }
        )

        pending = (
            await Payments.filter(
                userid=userid,
                paymentid=order_id,
                paymentstatus="created",
            )
            .prefetch_related(
                "productid"
            )
        )

        if not pending:

            raise HTTPException(
                404,
                "No pending payment"
            )

        tx = []

        async with (
            in_transaction()
            as conn
        ):

            for pay in pending:

                product = (
                    pay.productid
                )

                if not product:

                    raise HTTPException(
                        400,
                        "Missing product relation"
                    )

                if (
                    product.quantity
                    < 1
                ):
                    raise HTTPException(
                        400,
                        "Out of stock"
                    )

                await Product.filter(
                    id=product.id
                ).using_db(
                    conn
                ).update(
                    quantity=
                    product.quantity
                    - 1
                )

                pay.paymentstatus = (
                    "paid"
                )

                pay.paymentid = (
                    payment_id
                )

                await pay.save(
                    using_db=conn
                )

                t = (
                    await Transactions.create(
                        id=uuid.uuid4(),

                        userid=userid,

                        razorpaypaymentid=payment_id,

                        price=str(
                            pay.price
                        ),

                        using_db=conn,
                    )
                )

                tx.append(
                    {
                        "transaction_id":
                        str(t.id)
                    }
                )

        return {
            "message":
            "Payment verified",

            "payment_id":
            payment_id,

            "transactions":
            tx,
        }

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            500,
            f"Payment verification failed: {str(e)}"
        )


# ==================================================
# TRANSACTION HISTORY
# ==================================================
async def transaction_history(
    management_data:
    TransactionsHistoryUser
):

    userid = (
        management_data.user_id
    )

    rows = (
        await Transactions.filter(
            userid=userid
        )
    )

    history = []

    for row in rows:

        user = await User.get(
            id=row.userid
        )

        history.append({

            "id":
            str(row.id),

            "paymentid":
            row.razorpaypaymentid,

            "price":
            row.price,

            "fullname":
            user.name,
        })

    return {
        "count":
        len(history),

        "transactions":
        history,
    }