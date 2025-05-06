import uuid
from typing import Dict
from fastapi import HTTPException, status
from Database_and_ORM.Database_Models import Product, BuyNow, Address, Transactions
from logger import logger
from Data_Schemas import BuyNowSchema,PaymentSchema,TransactionsSchema,OrderSchema


async def buy_now(payload: Dict, buy_now_data: BuyNowSchema):
    userid = buy_now_data.user_id
    productid = buy_now_data.product_id
    address_id = buy_now_data.address_id
    quantity = int(buy_now_data.quantity)
    price = float(buy_now_data.price)

    # Validate the product exists and is in stock
    try:
        product = await Product.get(id=productid)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    if product.quantity < quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient stock for the requested quantity.",
        )

    # Validate the address exists for the user
    try:
        address = await Address.get(id=address_id, user_id=userid)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery address not found for the user.",
        )

    # Ensure only one product is being processed for Buy Now
    existing_entry = await BuyNow.filter(user_id=userid).first()
    if existing_entry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A 'Buy Now' transaction is already in progress. Complete it before starting a new one.",
        )

    try:
        # Decrement stock
        await Product.filter(id=productid).update(quantity=product.quantity - quantity)

        # Create a BuyNow entry
        new_entry = await BuyNow.create(
            id=uuid.uuid4(),
            user_id=userid,
            product_id=productid,
            address_id=address_id,
            quantity=quantity,
            price=price,
            payment_method=buy_now_data.payment_method,
            order_status="Pending",
        )
        return new_entry

    except Exception as e:
        logger.error(f"Error processing Buy Now: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process Buy Now: {str(e)}",
        )


async def get_buy_now_transactions(user_id: str):
   
    try:
        # Fetch all Buy Now entries for the user
        buy_now_entries = await BuyNow.filter(user_id=user_id).all()

        # If no records are found, raise an exception
        if not buy_now_entries:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No Buy Now transactions found for the user."
            )

        return buy_now_entries

    except Exception as e:
        print(f"Error fetching Buy Now transactions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred while fetching Buy Now transactions."
        )



# Initialize Razorpay client
razorpay_client = Client(auth=("RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET"))


async def razorpayfn(payment_schema:PaymentSchema):
    userid = payment_schema.user_id
    product_id = payment_schema.product_id
    quantity = payment_schema.quantity

    try:
        # Validate user existence
        user_entry = await User.get(id=userid)
        if not user_entry:
            raise HTTPException(status_code=404, detail="User not found")

        # Validate product existence and stock
        product_entry = await Product.get(id=product_id)
        if not product_entry:
            raise HTTPException(status_code=404, detail=f"Product {product_id} not found")

        if product_entry.quantity < quantity:
            raise HTTPException(status_code=400, detail="Insufficient stock for the requested quantity")

        # Calculate total amount
        total_amount = product_entry.price * quantity
        print(f"Total amount: {total_amount}")

        # Prepare Razorpay order data
        order_notes = {
            "productid": product_id,
            "quantity": quantity,
            "price_per_unit": product_entry.price
        }

        order_data = {
            "amount": int(total_amount) * 100,  # Razorpay expects amount in paise
            "currency": "INR",
            "receipt": f"receipt_{random.randint(1000, 9999)}",
            "notes": order_notes
        }

        # Create Razorpay order
        order = razorpay_client.order.create(data=order_data)
        print("Razorpay order created:", order)

        # Store payment details in database
        await Payments.create(
            userid=userid,
            productid=product_id,
            order_id=order["id"],
            price=total_amount,
            currency=order["currency"],
            paymentid=order["id"],
            paymentstatus=order["status"],
            receipt=order["receipt"],
            notes=order["notes"]
        )

        # Deduct stock after successful payment initiation
        await Product.filter(id=product_id).update(quantity=product_entry.quantity - quantity)

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


async def verifypayment(payload: dict, verify_payment:TransactionsSchema):
    userid = verify_payment.user_id
    razorpaypaymentid = verify_payment.razorpaypaymentid
    product_id = verify_payment.product_id
    price = verify_payment.price

    try:
        # Create a transaction entry for the single product
        transaction_entry = await Transactions.create(
            id=str(uuid.uuid4()),
            userid=userid,
            productid=product_id,
            razorpaypaymentid=razorpaypaymentid,
            price=price,
        )

        return {
            "message": "Payment verification record created successfully.",
            "transaction": transaction_entry
        }

    except Exception as e:
        print(f"Error in verifypayment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error occurred: {str(e)}"
        )


async def order_create(payload: Dict, order_data:OrderSchema):
    user_id = order_data.user_id
    delivery_address = order_data.deliveryaddress
    payment_option = order_data.paymentoption
    order_status = order_data.orderstatus
    product_id = order_data.product_id  # Single product ID
    quantity = int(order_data.quantity)  # Single product quantity

    try:
        # Validate the product exists and check stock
        try:
            product_entry = await Product.get(id=product_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product {product_id} not found.",
            )

        if product_entry.quantity < quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for product {product_id}.",
            )

        # Calculate total amount for the product
        total_amount = product_entry.price * quantity

        # Create a new order for the product
        new_order = await Order.create(
            id=str(uuid.uuid4()),
            userid=user_id,
            productid=product_id,
            ordered_quantity=quantity,
            totalamount=str(total_amount),
            paymentoption=payment_option,
            orderstatus=order_status,
            deliveryaddress=delivery_address,
        )

        # Deduct stock from the product
        await Product.filter(id=product_id).update(quantity=product_entry.quantity - quantity)

        return {"message": "Order created successfully.", "order": new_order}

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create order: {str(e)}"
        )