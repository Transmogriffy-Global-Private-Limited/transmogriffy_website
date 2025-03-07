import uuid
from fastapi import HTTPException, status, File, UploadFile
from tortoise.exceptions import DoesNotExist, IntegrityError
import re
import os
import shutil
import razorpay
from decouple import config
from .Data_Schemas import PaymentSchema
from Database_and_ORM.Database_Models import Payments, User, Product
import razorpay
import random
from decouple import config

# Ensure environment variables are set
razorpaykey = config('RAZOR_PAY_KEY')
razorpaysecret = config("RAZOR_PAY_SECRET")

# Initialize Razorpay client
razorpay_client = razorpay.Client(auth=(razorpaykey, razorpaysecret))

async def razorpayfn(payload: dict, payment_schema: PaymentSchema):
    
    # Extract necessary information from payment_schema
    userid = payment_schema.userid
    productid = payment_schema.paymentid
    price = payment_schema.price
    
    try:
        # Check if user exists
        user_entry = await User.get(id=userid)
        if not user_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User entry not found"
            )
        
        # Check if product exists
        product_entry = await Product.get(id=productid)
        if not product_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product entry not found"  # Corrected detail message
            )
        
        # Create order data for Razorpay
        order_data = {
            "amount": int(price) * 100, 
            "currency": "INR",
            "receipt": f"receipt_{random.randint(1000,9999)}",
            "notes": {
                "message": "data processing done"
            }
        }
        
        # Create a new order using Razorpay client
        order = razorpay_client.order.create(data=order_data)
        
        # Prepare payment data to save in the database
        payment_data = {
            "userid": userid,
            "productid": productid,
            "order_id": order['id'],
            "price": order['amount'],
            "currency": order['currency'],
            "status": order['status'],
            "receipt": order['receipt'],
            "notes": order['notes']
        }
        
        # Save payment details in the database
        new_order = await Payments.create(**payment_data)
        
        # Return a successful message
        return {"message": "Payment processed successfully", "order_id": order['id']}
    
    except DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Either user or product does not exist"
        )
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database integrity error. Please check your data."
        )
    except Exception as e:
        # Log the exception for debugging purposes
        print(f"An error occurred: {e}")
        
        # Return an error message
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred. Please try again later."
        )
