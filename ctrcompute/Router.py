from fastapi import APIRouter, status, Depends

from Utility_Methods.Utility_Methods import verify_admin_jwt
from .Database_Schemas import ClickEventSchema
from .Methods import track_click, get_click_analytics

ctrcompute_router = APIRouter()


@ctrcompute_router.post("/trackclick", status_code=status.HTTP_200_OK)
async def track_click_endpoint(
    click_event: ClickEventSchema,
):
    result = await track_click(click_event)
    return result


@ctrcompute_router.get("/getclickanalytics", status_code=status.HTTP_200_OK)
async def get_click_analytics_endpoint(
    admin_payload: dict = Depends(verify_admin_jwt),
):
    result = await get_click_analytics()
    return result
