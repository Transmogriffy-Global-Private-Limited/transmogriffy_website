import uuid
import logging
import random
import razorpay

from decouple import config
from fastapi import HTTPException, status
from sympy import python
from tortoise.exceptions import DoesNotExist
from tortoise.transactions import in_transaction
from uuid import UUID
import uuid

from fastapi import HTTPException
from tortoise.exceptions import DoesNotExist
from tortoise.transactions import in_transaction
from .Data_Schemas import (
    PaymentSchema,
    TransactionsHistoryUser,
    VerifyPaymentSchema,
    
)

from fastapi import HTTPException
from tortoise.transactions import in_transaction
from Database_and_ORM.Database_Models import (
    Payments,
    Order
)
from datetime import datetime
from datetime import timedelta
from Database_and_ORM.Database_Models import (
    Payments,
    User,
    Product,
    Transactions,
    InventoryReservation,
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
        # Validate + Reserve Inventory
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

            # -------------------------
            # Calculate active reserved qty
            # -------------------------
            reservations = (
                await InventoryReservation
                .filter(
                    product_id=item.productid,
                    converted=False,
                    released=False,
                    expired=False
                )
                .all()
            )

            reserved_qty = sum(
                r.quantity
                for r in reservations
            )

            available_stock = (
                product.quantity
                - reserved_qty
            )

            # -------------------------
            # Validate available stock
            # -------------------------
            if item.quantity > available_stock:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"{product.name} "
                        f"only "
                        f"{available_stock} "
                        f"available"
                    )
                )

            # -------------------------
            # Reserve inventory
            # -------------------------
            await InventoryReservation.create(

                user_id=userid,

                product_id=item.productid,

                quantity=item.quantity,

                expires_at=(
                    datetime.utcnow()
                    + timedelta(
                        minutes=5
                    )
                )
            )

            prices[
                item.productid
            ] = (
                product.price
            )

            total_amount += (
                product.price
                * item.quantity
            )

            order_notes.append({

                "product_id":
                str(
                    item.productid
                ),

                "quantity":
                item.quantity,

                "unit_price":
                product.price
            })

        # -----------------------------
        # Create Razorpay Order
        # -----------------------------
        order = (
            razorpay_client
            .order
            .create(
                {
                    "amount":
                    int(
                        total_amount
                        * 100
                    ),

                    "currency":
                    "INR",

                    "receipt":
                    (
                        f"receipt_"
                        f"{random.randint(1000,9999)}"
                    ),

                    "notes": {
                        "products":
                        order_notes
                    }
                }
            )
        )

        # -----------------------------
        # Save Payment Rows
        # -----------------------------
        for item in products:

            await Payments.create(

                userid=userid,

                productid=str(
                    item.productid
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

                paymentstatus="created",

                receipt=order[
                    "receipt"
                ],

                notes=order[
                    "notes"
                ]
            )

        return {

            "message":
            (
                "Payment initiated. "
                "Inventory reserved "
                "for 5 minutes."
            ),

            "order_id":
            order["id"],

            "amount":
            total_amount,

            "expires_in":
            "5 minutes"
        }

    except DoesNotExist:

        raise HTTPException(
            status_code=404,
            detail=(
                "User/Product "
                "not found"
            )
        )

    except HTTPException:
        raise

    except Exception as e:

        logger.exception(
            "Create payment failed"
        )

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ==================================================
# VERIFY PAYMENT
# ==================================================
async def verifypayment(
    verify_payment: VerifyPaymentSchema
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

        if not payment_id:
            raise HTTPException(
                400,
                "razorpay_payment_id required"
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

        # -------------------------
        # Verify Signature
        # -------------------------

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

        # -------------------------
        # Load Payment Rows
        # -------------------------

        pending = (
            await Payments
            .filter(
                userid=userid,
                paymentid=order_id,
                paymentstatus="created",
            )
            .all()
        )

        if not pending:

            raise HTTPException(
                404,
                "No pending payment"
            )

        tx = []

        async with in_transaction() as conn:

            for pay in pending:

                if not pay.productid:

                    raise HTTPException(
                        400,
                        "Missing productid"
                    )

                try:

                    product_uuid = UUID(
                        str(
                            pay.productid
                        )
                    )

                except ValueError:

                    raise HTTPException(
                        400,
                        "Invalid productid"
                    )

                # -------------------------
                # Load Reservation
                # -------------------------

                reservation = (
                    await InventoryReservation
                    .filter(
                        user_id=userid,
                        product_id=product_uuid,
                        converted=False,
                        released=False,
                        expired=False,
                    )
                    .using_db(conn)
                    .first()
                )

                if not reservation:

                    raise HTTPException(
                        400,
                        (
                            "Reservation "
                            "not found "
                            "or expired"
                        )
                    )

                # -------------------------
                # Expiry Check
                # -------------------------

                if (
                    reservation.expires_at
                    < datetime.utcnow()
                ):

                    reservation.expired = True

                    reservation.released = True

                    await reservation.save(
                        using_db=conn
                    )

                    raise HTTPException(
                        400,
                        (
                            "Payment timeout "
                            "(5 min exceeded)"
                        )
                    )

                # -------------------------
                # Load Product
                # -------------------------

                product = (
                    await Product
                    .get(
                        id=product_uuid
                    )
                    .using_db(conn)
                )

                # -------------------------
                # Final Validation
                # -------------------------

                if (
                    product.quantity
                    <
                    reservation.quantity
                ):

                    raise HTTPException(
                        400,
                        (
                            "Insufficient "
                            "inventory"
                        )
                    )

                # -------------------------
                # Deduct Stock
                # -------------------------

                await (
                    Product
                    .filter(
                        id=product_uuid
                    )
                    .using_db(conn)
                    .update(
                        quantity=(
                            product.quantity
                            -
                            reservation.quantity
                        )
                    )
                )

                # -------------------------
                # Convert Reservation
                # -------------------------

                reservation.converted = True

                await reservation.save(
                    using_db=conn
                )

                # -------------------------
                # Update Payment
                # -------------------------

                pay.paymentstatus = (
                    "paid"
                )

                pay.paymentid = (
                    payment_id
                )

                await pay.save(
                    using_db=conn
                )

                # -------------------------
                # Transaction
                # -------------------------

                t = (
                    await Transactions.create(

                        id=uuid.uuid4(),

                        userid=str(
                            userid
                        ),

                        productid=str(
                            product_uuid
                        ),

                        razorpaypaymentid=(
                            payment_id
                        ),

                        price=str(
                            pay.price
                        ),

                        using_db=conn
                    )
                )

                tx.append(
                    {
                        "transaction_id":
                        str(
                            t.id
                        ),

                        "productid":
                        str(
                            product_uuid
                        ),

                        "price":
                        str(
                            pay.price
                        )
                    }
                )

        return {

            "message":
            (
                "Payment verified "
                "and stock deducted"
            ),

            "order_id":
            order_id,

            "payment_id":
            payment_id,

            "transactions":
            tx
        }

    except HTTPException:
        raise

    except DoesNotExist:

        raise HTTPException(
            404,
            "Product not found"
        )

    except Exception as e:

        logger.exception(
            "Payment verification failed"
        )

        raise HTTPException(
            status_code=500,

            detail=(
                "Payment verification failed: "
                f"{str(e)}"
            )
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



async def payment_failed_fn(
    order_id: str
):

    async with in_transaction() as conn:

        payments = await (
            Payments
            .filter(
                paymentid=order_id,
                paymentstatus="created"
            )
            .using_db(conn)
            .all()
        )

        if not payments:

            raise HTTPException(
                status_code=404,
                detail="No pending payment found"
            )

        await (
            Payments
            .filter(
                paymentid=order_id
            )
            .using_db(conn)
            .update(
                paymentstatus="failed"
            )
        )

        await (
            Order
            .filter(
                rzp_order_id=order_id
            )
            .using_db(conn)
            .update(
                orderstatus="cancelled"
            )
        )

    return {

        "message":
        "Payment marked as failed",

        "order_id":
        order_id
    }

async def release_payment(
    order_id
):

    rows=await Payments.filter(
        paymentid=order_id,
        paymentstatus="created"
    )

    for p in rows:

        await (
            InventoryReservation
            .filter(
                user_id=p.userid,
                product_id=p.productid,
                converted=False
            )
            .update(
                released=True
            )
        )

        p.paymentstatus="failed"

        await p.save()

    return {
        "message":
        "Reservation released"
    }


async def expire_reservations():

    now=datetime.utcnow()

    rows=(
        await InventoryReservation
        .filter(
            expires_at__lt=now,
            converted=False,
            released=False
        )
    )

    for r in rows:

        r.expired=True

        r.released=True

        await r.save()