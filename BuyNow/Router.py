
from fastapi import (
    APIRouter,
    Depends,
    Header,
    status,
    HTTPException,
)
from typing import Dict
from .Methods import buy_now,get_buy_now_transactions,razorpayfn,verifypayment
from .Data_Schemas import BuyNowSchema,PaymentSchema,TransactionsSchema,OrderSchema

buynow_router = APIRouter()

@buynow_router.post("/buy_now",status_code=status.HTTP_200_OK)
async def buy_now_endpoint(payload: Dict, buy_now_data: BuyNowSchema):
    return await buy_now(payload, buy_now_data)

@buynow_router.post("/getbuynowtransactions",status_code=status.HTTP_200_OK)
async def get_buy_now_transactions_endpoint(user_id: str):
    return await get_buy_now_transactions(user_id)

@buynow_router.post("/razorpayfn",status_code=status.HTTP_200_OK)
async def razorpayfn_endpoint(payload: Dict, payment_data: PaymentSchema):
    return await razorpayfn(payload, payment_data)

@buynow_router.post("/verifypayment",status_code=status.HTTP_200_OK)
async def verifypayment_endpoint(payload: Dict, verify_payment: TransactionsSchema):
    return await verifypayment(payload, verify_payment)

@buynow_router.post("/order_create",status_code=status.HTTP_200_OK)
async def order_create_endpoint(payload: Dict, order_data: OrderSchema):
    return await order_create(payload, order_data)
