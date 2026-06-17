import uuid
import logging
import random
import razorpay
from decouple import config
from fastapi import HTTPException, status
from tortoise.exceptions import DoesNotExist, IntegrityError
from tortoise.transactions import in_transaction

# Schema and Model mappings
from .Data_Schemas import PaymentSchema, TransactionsSchema, TransactionsHistoryUser, VerifyPaymentSchema
from Database_and_ORM.Database_Models import (
    Payments,
    User,
    Product,
    Transactions,
)

logger = logging.getLogger("Payments.Methods")
logger.setLevel(logging.DEBUG)

razorpaykey = config("RAZOR_PAY_KEY")
razorpaysecret = config("RAZOR_PAY_SECRET")

razorpay_client = razorpay.Client(auth=(razorpaykey, razorpaysecret))

# -----------------------------------------------------------------------------
# 1. INITIALIZE RAZORPAY ORDER FLOW
# -----------------------------------------------------------------------------
async def razorpayfn(payment_schema: PaymentSchema):

    userid = payment_schema.user_id
    products = payment_schema.products

    try:

        await User.get(id=userid)

        total_amount = 0
        order_notes = []
        product_prices = {}

        for item in products:

            if not item.productid:
                raise HTTPException(
                    status_code=400,
                    detail="productid cannot be empty"
                )

            product_entry = await Product.get(
                id=item.productid
            )

            item_total = product_entry.price * item.quantity

            total_amount += item_total

            product_prices[item.productid] = (
                product_entry.price
            )

            order_notes.append({
                "product_id": item.productid,
                "quantity": item.quantity,
                "price_per_unit": product_entry.price
            })

        order = razorpay_client.order.create({
            "amount": int(total_amount * 100),
            "currency": "INR",
            "receipt": f"receipt_{random.randint(1000,9999)}",
            "notes": {
                "orders": order_notes
            }
        })

        for item in products:

            await Payments.create(
                userid=userid,
                productid=str(item.productid),
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

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

# -----------------------------------------------------------------------------
# 2. VERIFY PAYMENT (Aligned to Frontend JSON structure)
# -----------------------------------------------------------------------------
async def verifypayment(
    verify_payment: VerifyPaymentSchema
):

    try:

        payment_token = (
            verify_payment.razorpay_payment_id
        )

        userid = (
            verify_payment.user_id
        )

        order_id = (
            verify_payment.razorpay_order_id
        )

        signature = (
            verify_payment.razorpay_signature
        )

        if not order_id:
            raise HTTPException(
                400,
                "razorpay_order_id required"
            )

        if not signature:
            raise HTTPException(
                400,
                "razorpay_signature required"
            )

        razorpay_client.utility.verify_payment_signature({
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_token,
            "razorpay_signature": signature
        })

        pending = await Payments.filter(
            userid=userid,
            paymentid=order_id,
            paymentstatus="created"
        )

        if not pending:
            raise HTTPException(
                404,
                "No pending payment"
            )

        tx = []

        async with in_transaction() as connection:

            for payment in pending:

                if payment.productid is None:
                    raise HTTPException(
                        400,
                        f"Payment {payment.id} missing productid"
                    )

                product = await Product.get(
                    id=payment.productid
                )

                if product.quantity < 1:
                    raise HTTPException(
                        400,
                        "Product out of stock"
                    )

                await Product.filter(
                    id=payment.productid
                ).using_db(
                    connection
                ).update(
                    quantity=product.quantity - 1
                )

                payment.paymentstatus = "paid"
                payment.paymentid = payment_token

                await payment.save(
                    using_db=connection
                )

                t = await Transactions.create(
                    id=uuid.uuid4(),
                    userid=payment.userid,
                    razorpaypaymentid=payment_token,
                    price=str(payment.price),
                    using_db=connection
                )

                tx.append({
                    "transaction_id": str(t.id)
                })

        return {
            "message": "Payment verified",
            "payment_id": payment_token,
            "transactions": tx
        }

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            500,
            f"Payment verification failed: {str(e)}"
        )
    
# -----------------------------------------------------------------------------
# 3. TRANSACTION HISTORY LOOKUPS
# -----------------------------------------------------------------------------
async def transaction_history(
    management_data: TransactionsHistoryUser
):
    try:

        userid = management_data.user_id

        if not userid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user_id is required"
            )

        rows = await Transactions.filter(
            userid=userid
        ).all()

        history = []

        for row in rows:

            user = await User.get(
                id=row.userid
            )

            history.append({
                "id": str(row.id),
                "paymentid": row.razorpaypaymentid,
                "price": row.price,
                "userid": row.userid,
                "fullname": user.name,
            })

        return {
            "message": "Transaction history fetched successfully",
            "count": len(history),
            "transactions": history
        }

    except HTTPException as http_exc:
        raise http_exc

    except DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    except Exception as e:

        logger.error(
            f"Failed to fetch transaction history: {str(e)}"
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch transaction history: {str(e)}",
        )