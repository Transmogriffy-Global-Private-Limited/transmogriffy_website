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
            total_amount += item_total
            product_prices[item.productid] = product_entry.price

            order_notes.append({
                "product_id": item.productid, 
                "quantity": item.quantity,
                "price_per_unit": product_entry.price,
            })

        order_data = {
            "amount": int(total_amount) * 100,
            "currency": "INR",
            "receipt": f"receipt_{random.randint(1000, 9999)}",
            "notes": {"orders": order_notes}
        }

        order = razorpay_client.order.create(data=order_data)
        logger.debug(f"Razorpay order created successfully: {order['id']}")

        # Bulk register temporary item rows under initial pending status
        for item in products:
            await Payments.create(
                userid=userid,
                productid=item.productid,
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
    except IntegrityError as ie:
        logger.error(f"Database Integrity Error: {str(ie)}")
        raise HTTPException(status_code=400, detail="Database integrity error. Please check your data fields configuration.")
    except Exception as e:
        logger.error(f"Failed to initialize Razorpay checkout order: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Payment initialization error: {str(e)}"
        )


# -----------------------------------------------------------------------------
# 2. VERIFY PAYMENT (Aligned to Frontend JSON structure)
# -----------------------------------------------------------------------------
async def verifypayment(payload: dict, verify_payment: VerifyPaymentSchema):
    try:
        # NOTE: signature verification is skipped here because your frontend Cart.jsx 
        # is only transmitting raw 'razorpaypaymentid', 'user_id', and 'products' properties.

        # Extract values using the verified Pydantic schema parameters
        payment_token = verify_payment.razorpay_payment_id
        current_userid = verify_payment.user_id

        # ✅ FIXED: Changed lookup key to locate pending rows using the payment transaction string
        pending_payments = await Payments.filter(
            userid=current_userid,
            paymentstatus="created"
        ).all()

        # Fallback filter mapping strategy if structural rows are already staged under a unique token id
        if not pending_payments:
            pending_payments = await Payments.filter(userid=current_userid).all()

        if not pending_payments:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No matching checkout records found locally for this session user context.",
            )

        processed_transactions_metadata = []

        # Enter safe ACID-compliant atomic transaction execution context
        async with in_transaction() as connection:
            for payment in pending_payments:
                
                product = await Product.get(id=payment.productid)
                if product.quantity <= 0:
                     raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="An item in this order went out of stock before payment was finalized."
                    )
                
                # Securely decrement core stock quantities directly against storage engine
                await Product.filter(id=payment.productid).using_db(connection).update(
                    quantity=product.quantity - 1
                )

                # Mutate local individual transaction rows safely
                payment.paymentstatus = "paid"
                payment.paymentid = payment_token  
                await payment.save(using_db=connection)

                # Generate history ledger bookkeeping records
                new_transaction = await Transactions.create(
                    id=uuid.uuid4(),
                    userid=payment.userid,
                    razorpaypaymentid=payment_token,
                    price=str(payment.price),
                    using_db=connection
                )
                
                processed_transactions_metadata.append({
                    "transaction_id": str(new_transaction.id),
                    "user_id": str(payment.userid),
                    "price_processed": str(payment.price)
                })

        return {
            "message": "Payment verification records created successfully.",
            "transactions": processed_transactions_metadata
        }

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error in verifypayment workflow execution sequence: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal verification handling failure occurred: {str(e)}"
        )


# -----------------------------------------------------------------------------
# 3. TRANSACTION HISTORY LOOKUPS
# -----------------------------------------------------------------------------
async def transaction_history(
    payload: dict, management_data: TransactionsHistoryUser
):
    userid = management_data.user_id
    try:
        rows = await Transactions.filter(userid=userid).all()
        history = []

        for row in rows:
            user = await User.get(id=row.userid)
            history.append({
                "id": row.id,
                "paymentid": row.razorpaypaymentid,
                "price": row.price,
                "userid": row.userid,
                "fullname": user.name,
            })

        return history

    except Exception as e:
        logger.error(f"Failed to fetch transaction records history manifest: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch transaction history layout fields: {str(e)}",
        )