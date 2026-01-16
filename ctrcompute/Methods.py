from fastapi import APIRouter, HTTPException, status
from Database_and_ORM.Database_Models import ClickEvent
from ctrcompute.Database_Schemas import ClickEventSchema
import logging
from typing import Dict
from collections import defaultdict

logger = logging.getLogger(__name__)


# {
#   "user_id": "user_123",
#   "session_id": "sess_abc",
#   "page_url": "https://example.com/products",
#   "element_id": "buy-now-button",
#   "element_class": "btn-primary",
#   "element_text": "Buy Now",
#   "click_x": 200,
#   "click_y": 350,
#   "referrer": "https://google.com",
#   "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
#   "ip_address": "203.0.113.5"
# }


# import React from "react";

# function TrackableButton() {
#   const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
#     const click_x = e.clientX; // X coordinate relative to the viewport
#     const click_y = e.clientY; // Y coordinate relative to the viewport

#     console.log("Click coordinates:", { click_x, click_y });

#     // Send to backend
#     fetch("/api/track-click", {
#       method: "POST",
#       headers: {
#         "Content-Type": "application/json",
#       },
#       body: JSON.stringify({
#         user_id: "user_123",
#         session_id: "session_abc",
#         page_url: window.location.href,
#         element_id: e.currentTarget.id,
#         element_class: e.currentTarget.className,
#         element_text: e.currentTarget.innerText,
#         click_x,
#         click_y,
#         referrer: document.referrer,
#         user_agent: navigator.userAgent,
#         ip_address: null // Optional: backend should detect
#       }),
#     });
#   };

#   return (
#     <button
#       id="buy-now-btn"
#       className="btn-primary"
#       onClick={handleClick}
#     >
#       Buy Now
#     </button>
#   );
# }

# export default TrackableButton;



async def track_click(payload: ClickEventSchema):
    try:
        new_click = await ClickEvent.create(
            user_id=payload.user_id,
            session_id=payload.session_id,
            page_url=payload.page_url,
            element_id=payload.element_id,
            element_class=payload.element_class,
            element_text=payload.element_text,
            click_x=payload.click_x,
            click_y=payload.click_y,
            referrer=payload.referrer,
            user_agent=payload.user_agent,
            ip_address=payload.ip_address,
        )
        return {"status": "success", "click_id": new_click.id}
    
    except DBError as e:
        logger.error(f"DB Error saving click: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save click event.",
        )

async def get_click_analytics():
    try:
        events = await ClickEvent.all()
        if not events:
            return {"message": "No click events found."}

        total_clicks = len(events)
        unique_sessions = set(event.session_id for event in events if event.session_id)

        # CTR by element_id and page_url
        ctr_by_element: Dict[str, int] = defaultdict(int)
        ctr_by_page: Dict[str, int] = defaultdict(int)

        for event in events:
            if event.element_id:
                ctr_by_element[event.element_id] += 1
            ctr_by_page[event.page_url] += 1

        # Format results for easier frontend use
        result = {
            "total_clicks": total_clicks,
            "unique_sessions": len(unique_sessions),
            "ctr_by_element": dict(ctr_by_element),
            "ctr_by_page": dict(ctr_by_page),
        }

        return result

    except Exception as e:
        logger.error(f"Failed to get click analytics: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch click analytics."
        )