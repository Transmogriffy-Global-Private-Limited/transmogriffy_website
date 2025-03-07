from fastapi import (
    APIRouter,
    Depends,
    Header,
    status,
    HTTPException,
)
from .Methods import razorpayfn
from .Data_Schemas import PaymentSchema

payment_router = APIRouter()

@payment_router.post("/createpayment", status_code=status.HTTP_200_OK)
async def payment_endpoint(payment_data: PaymentSchema):
    
    try:
        # Call the function to create a Razorpay order and save payment details
        result = await razorpayfn({}, payment_data)
        
        # Return the result if successful
        return result
    
    except HTTPException as e:
        # Re-raise the HTTPException to maintain the status code and detail
        raise e
    
    except Exception as e:
        # Log the exception for debugging purposes
        print(f"An error occurred: {e}")
        
        # Return an error message
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred. Please try again later."
        )
