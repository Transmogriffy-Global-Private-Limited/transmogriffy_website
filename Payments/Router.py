import uuid
from fastapi import (
    APIRouter,
    Depends,
    Header,
    status,
    HTTPException,
)
from sympy import python
from .Methods import razorpayfn, verifypayment, transaction_history
from .Data_Schemas import PaymentSchema, TransactionsSchema, TransactionsHistoryUser, VerifyPaymentSchema

payment_router = APIRouter()

# ----------------------------------------
# Create Payment (Initialize Razorpay Order)
# ----------------------------------------
@payment_router.post("/createpayment", status_code=status.HTTP_200_OK)
async def payment_endpoint(payment_data: PaymentSchema):
    try:
        result = await razorpayfn(payment_data)
        return result

    except HTTPException as he:
        raise he

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment initialization gateway breakdown: {str(e)}",
        )


# ----------------------------------------
# Verify Payment (Signature Verification)
# ----------------------------------------
@payment_router.post(
    "/verifypayment",
    status_code=status.HTTP_200_OK,
)
async def verify_payment_endpoint(
    verify_ep: VerifyPaymentSchema,
):
    try:
        # Forward validated request body directly
        result = await verifypayment(
            verify_payment=verify_ep
        )

        return result

    except HTTPException as he:
        raise he

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cryptographic signature processing execution sequence failure: {str(e)}",
        )


# ----------------------------------------
# User Transaction History
# ----------------------------------------
@payment_router.post(
    "/usertransactionhistory",
    status_code=status.HTTP_200_OK,
)
async def user_transaction_history(
    th_of_u: TransactionsHistoryUser,
):
    try:
        # ✅ FIXED: Removed the empty dict '{}' positional argument blocker
        # so that th_of_u parameters are parsed correctly by transaction_history
        result = await transaction_history(th_of_u)
        return result

    except HTTPException as he:
        raise he

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to aggregate customer accounting transaction ledgers: {str(e)}",
        )
    
@payment_router.post(
    "/paymentfailed"
)
async def payment_failed(
    order_id: str
):
    return {
        "message": "ok"
    }
