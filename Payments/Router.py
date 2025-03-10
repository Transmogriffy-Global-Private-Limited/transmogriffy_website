from fastapi import (
    APIRouter,
    Depends,
    Header,
    status,
    HTTPException,
)
from .Methods import razorpayfn,verifypayment,transaction_history
from .Data_Schemas import PaymentSchema, Transactions,TransactionsHistoryUser

payment_router = APIRouter()

@payment_router.post("/createpayment", status_code=status.HTTP_200_OK)
async def payment_endpoint(payment_data: PaymentSchema):
    
    try:
        result = await razorpayfn({}, payment_data)
        return result
    
    except HTTPException as e:
        raise e
    
    except Exception as e:
        print(f"An error occurred: {e}")
      
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred. Please try again later."
        )

@payment_router.post("/verifypayment",status_code=status.HTTP_200_OK)
async def verify_payment_endpoint(verify_ep:Transactions):
    try:
        result = await verifypayment({},verify_ep)
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred. Please try again later."
        )
    
@payment_router.post("/usertransactionhistory", status_code=status.HTTP_200_OK)
async def user_transaction_history(th_of_u:TransactionsHistoryUser):
    try:
        result = await transaction_history({},th_of_u)
        return result
    except HTTPException as e:
        raise e
        
    except Exception as e:
        print(e)