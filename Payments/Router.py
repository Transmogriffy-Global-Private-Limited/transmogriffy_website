# Payments/Router.py

from fastapi import (
    APIRouter,
    status,
    HTTPException,
)

from .Methods import (
    razorpayfn,
    verifypayment,
    transaction_history,
)

from .Data_Schemas import (
    PaymentSchema,
    VerifyPaymentSchema,
    TransactionsHistoryUser,
)

payment_router = APIRouter()


# ----------------------------------------
# Create Razorpay Payment Order
# ----------------------------------------
@payment_router.post(
    "/createpayment",
    status_code=status.HTTP_200_OK,
)
async def payment_endpoint(
    payment_data: PaymentSchema,
):
    try:
        result = await razorpayfn(payment_data)
        return result

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


# ----------------------------------------
# Verify Payment (signature verification)
# ----------------------------------------
@payment_router.post(
    "/verifypayment",
    status_code=status.HTTP_200_OK,
)
async def verify_payment_endpoint(
    verify_ep: VerifyPaymentSchema,
):
    try:
        result = await verifypayment(
            {},
            verify_ep,
        )

        return result

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
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
        result = await transaction_history(
            {},
            th_of_u,
        )

        return result

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )