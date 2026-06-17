from fastapi import (
    APIRouter,
    Depends,
    Header,
    status,
    HTTPException,
)
from .Methods import razorpayfn, verifypayment, transaction_history
from .Data_Schemas import PaymentSchema, TransactionsSchema, TransactionsHistoryUser

payment_router = APIRouter()


@payment_router.post("/createpayment", status_code=status.HTTP_200_OK)
async def payment_endpoint(payment_data: PaymentSchema):
        result = await razorpayfn(payment_data)
        return result

@payment_router.post("/verifypayment", status_code=status.HTTP_200_OK)
async def verify_payment_endpoint(verify_ep: TransactionsSchema):
        result = await verifypayment({}, verify_ep)
        return result




@payment_router.post("/usertransactionhistory", status_code=status.HTTP_200_OK)
async def user_transaction_history(th_of_u: TransactionsHistoryUser):
    try:
        result = await transaction_history({}, th_of_u)
        return result
    except HTTPException as e:
        raise e

    except Exception as e:
        print(e)
