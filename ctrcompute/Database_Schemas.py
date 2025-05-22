from pydantic import BaseModel, Field
from typing import Optional


class ClickEventSchema(BaseModel):
    user_id: Optional[str]
    session_id: Optional[str]
    page_url: str
    element_id: Optional[str]
    element_class: Optional[str]
    element_text: Optional[str]
    click_x: Optional[int]
    click_y: Optional[int]
    referrer: Optional[str]
    user_agent: Optional[str]
    ip_address: Optional[str]
