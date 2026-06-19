from fastapi import APIRouter, Body, status, HTTPException, Depends
from pydantic import BaseModel

from Utility_Methods.Utility_Methods import verify_admin_jwt
from .Methods import (
    product_analytics,
    product_stock_analysis,
    total_sales,
    user_purchase_summary,
    user_total_spent_and_orders,
)

analytics_router = APIRouter()


class UserPurchaseSummaryRequest(BaseModel):
    user_id: str


@analytics_router.get("/product_analytics", status_code=status.HTTP_200_OK)
async def get_product_analytics(admin_payload: dict = Depends(verify_admin_jwt)):
    try:
        analytics = await product_analytics()
        return {"product_analytics": analytics}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch product analytics: {str(e)}",
        )


@analytics_router.get("/product_stock_analysis", status_code=status.HTTP_200_OK)
async def get_product_stock_analysis(admin_payload: dict = Depends(verify_admin_jwt)):
    try:
        analysis = await product_stock_analysis()
        return {"product_stock_analysis": analysis}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch product stock analysis: {str(e)}",
        )


@analytics_router.get("/total_sales", status_code=status.HTTP_200_OK)
async def get_total_sales(admin_payload: dict = Depends(verify_admin_jwt)):
    try:
        total = await total_sales()
        return {"total_sales": total}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch total sales: {str(e)}",
        )


@analytics_router.post("/user_purchase_summary", status_code=status.HTTP_200_OK)
async def get_user_purchase_summary(
    request: UserPurchaseSummaryRequest = Body(...),
    admin_payload: dict = Depends(verify_admin_jwt),
):
    try:
        summary = await user_purchase_summary(request.user_id)
        return {"user_purchase_summary": summary}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user purchase summary: {str(e)}",
        )


@analytics_router.post("/user_total_spent_and_orders", status_code=status.HTTP_200_OK)
async def get_user_total_spent_and_orders(
    request: UserPurchaseSummaryRequest = Body(...),
    admin_payload: dict = Depends(verify_admin_jwt),
):
    try:
        result = await user_total_spent_and_orders(request.user_id)
        return {"user_total_spent_and_orders": result}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user total spent and orders: {str(e)}",
        )
