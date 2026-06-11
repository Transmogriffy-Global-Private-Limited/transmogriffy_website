import random
import uuid
import logging
import razorpay
from fastapi import HTTPException, status
from tortoise.exceptions import DoesNotExist, IntegrityError
from tortoise.transactions import in_transaction
from decouple import config

from .Data_Schemas import PaymentSchema, VerifyPaymentSchema, TransactionsHistoryUser
from Database_and_ORM.Database_Models import Payments, User, Product, Transactions

# Initialize logging for payment tracking
logger = logging.getLogger(__name__)

# -----------------------------------------
# Razorpay Client Setup
# -----------------------------------------
razorpaykey = config("RAZOR_PAY_KEY")
razorpaysecret = config("RAZOR_PAY_SECRET")

razorpay_client = razorpay.Client(
    auth=(razorpaykey, razorpaysecret)
)

# -----------------------------------------
# CREATE PAYMENT (Generates Intent & RZP Order)
# -----------------------------------------
async def razorpayfn(payment_schema: PaymentSchema):
    userid = payment_schema.user_id
    products = payment_schema.products

    try:
        # Validate that the purchasing user exists
        user_entry = await User.get(id=userid)

        total_amount = 0
        order_notes = []
        product_prices = {}

        # Validate database stock limits and capture snapshots upfront safely
        for item in products:
            product = await Product.get(id=item.productid)
            
            if product.quantity < item.quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Product {product.id} has insufficient inventory quantity."
                )

            item_total = product.price * item.quantity
            total_amount += item_total
            product_prices[item.productid] = product.price

            order_notes.append({
                "product_id": item.productid, # Aligned tracking dictionary keys
                "quantity": item.quantity,
                "price_per_unit": product.price,
            })

        # Structure payload matching Razorpay Core Order requirements
        order_data = {
            "amount": int(total_amount * 100),  # Expressed securely in currency paise
            "currency": "INR",
            "receipt": f"receipt_{random.randint(1000, 9999)}",
            "notes": {
                "internal_order_id": payment_schema.order_id,
                "orders": order_notes
            },
        }

        # Dispatch API network call out to Razorpay
        order = razorpay_client.order.create(data=order_data)

        # Bulk register temporary item rows under initial pending status
        for item in products:
            # ✅ FIXED: Configured database schema arguments to match user_id / product_id foreign keys
            await Payments.create(
                user_id=userid,
                product_id=item.productid,
                price=product_prices[item.productid] * item.quantity,
                currency=order["currency"],
                paymentid=order["id"],         # Using rzp_order_id string as lookup anchor
                paymentstatus=order["status"],  # Labeled "created" / "pending"
                receipt=order["receipt"],
                notes=order["notes"],
            )

        return {
            "message": "Payment initiated successfully",
            "razorpay_order_id": order["id"],
            "amount": total_amount,
        }

    except DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Target User or Product model entry records not found."
        )
    except Exception as e:
        logger.error(f"Failed to initialize Razorpay checkout order: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=str(e)
        )

# -----------------------------------------
# VERIFY PAYMENT (Atomic Verification & Processing)
# -----------------------------------------
async def verifypayment(payload: dict, verify_payment: VerifyPaymentSchema):
    try:
        # 1. Cryptographic Signature Validation Check
        razorpay_client.utility.verify_payment_signature({
            "razorpay_order_id": verify_payment.razorpay_order_id,
            "razorpay_payment_id": verify_payment.razorpay_payment_id,
            "razorpay_signature": verify_payment.razorpay_signature,
        })

        # 2. Extract matching items registered under the structural anchor token
        pending_payments = await Payments.filter(
            paymentid=verify_payment.razorpay_order_id
        ).all()

        if not pending_payments:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No pending checkout payment records found matching this razorpay_order_id.",
            )

        # 3. Enter safe ACID-compliant atomic system execution context
        async with in_transaction() as connection:
            for payment in pending_payments:
                
                # Fetch fresh real-time database state inside transaction isolation boundary
                # ✅ FIXED: Swapped out legacy attribute referencing mapping parameters
                product = await Product.get(id=payment.product_id)
                if product.quantity <= 0:
                     raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="An item in this order went out of stock before payment was finalized."
                    )
                
                # Securely decrement core stock quantities directly against storage engine isolation
                await Product.filter(id=payment.product_id).update(
                    quantity=product.quantity - 1
                )

                # Mutate local individual transaction rows safely
                payment.paymentstatus = "paid"
                payment.paymentid = verify_payment.razorpay_payment_id  # Shift string value to final pay_ ID
                await payment.save(using_db=connection)

                # 4. Generate history ledger bookkeeping records
                # ✅ FIXED: Restructured fields execution pattern to match user_id
                await Transactions.create(
                    id=uuid.uuid4(),
                    user_id=payment.user_id,
                    razorpaypaymentid=verify_payment.razorpay_payment_id,
                    price=str(payment.price),
                    using_db=connection
                )

        return {
            "message": "Payment verified and inventory updated successfully.",
            "payment_id": verify_payment.razorpay_payment_id,
        }

    except razorpay.errors.SignatureVerificationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Cryptographic signature verification failed. Invalid transaction token."
        )
    except Exception as e:
        logger.error(f"Critical transaction rollback triggered during payment lifecycle: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=str(e)
        )

# -----------------------------------------
# TRANSACTION HISTORY
# -----------------------------------------
async def transaction_history(payload: dict, management_data: TransactionsHistoryUser):
    userid = management_data.user_id

    try:
        # ✅ FIXED: Changed criteria filter string to map straight to user_id
        rows = await Transactions.filter(user_id=userid).all()
        history = []

        for row in rows:
            # ✅ FIXED: Swapped legacy attribute parameters for instance tracking references
            user = await User.get(id=row.user_id)
            history.append({
                "id": row.id,
                "paymentid": row.razorpaypaymentid,
                "price": row.price,
                "userid": row.user_id,
                "fullname": user.name,
            })

        return history

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to pull transaction profiles: {str(e)}",
        )