from .Database_Schemas import ClickEventSchema
from .Methods import track_click
from fastapi import APIRouter, status

ctrcompute_router = APIRouter()

@ctrcompute_router.post("/trackclick", status_code=status.HTTP_200_OK)
async def track_click_endpoint(
    click_event: ClickEventSchema,
):
    result = await track_click(click_event)
    return result
