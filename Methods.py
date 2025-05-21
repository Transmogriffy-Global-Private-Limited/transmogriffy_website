from Database_and_ORM.Methods import init_db, close_db
from Database_and_ORM.Database_Models import APIActivityLog
from datetime import datetime, timezone
from fastapi import Request, HTTPException, status, Header
from fastapi.responses import StreamingResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from decouple import config
import traceback
from typing import Optional, Callable
import asyncio


async def startup_event():
    await init_db()


async def shutdown_event():
    await close_db()


class VerifyAPIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        """
        Middleware to check for a valid API key in the request headers, excluding certain paths.
        """
        # List of paths to exclude from API key verification
        excluded_paths = config("EXCLUDED_PATHS")

        # Skip validation if the path is in the excluded paths
        if request.url.path in excluded_paths:
            return await call_next(request)

        # Fetch API key from request headers and compare with the valid key
        api_key = request.headers.get("API-KEY")
        valid_api_key = config("API_KEY")

        if not api_key:
            return JSONResponse(
                status_code=401, content={"detail": "No API key present"}
            )

        if api_key != valid_api_key:
            return JSONResponse(
                status_code=403, content={"detail": "Invalid API Key"}
            )

        response = await call_next(request)
        return response


async def log_api_activity(
    request: Request,
    response_status: Optional[int] = None,
    response_time: Optional[int] = None,  # Integer value in milliseconds
    error: Optional[str] = None,  # Capture error as a string
    error_location: Optional[str] = None,
):
    """
    Logs API activity to the database.
    """
    endpoint_hit = request.url.path
    requesting_ip = request.client.host

    # Capture selected request details
    request_data = {
        "headers": dict(request.headers),
        "user_agent": request.headers.get("User-Agent"),
    }

    # Capture request body if possible
    try:
        request_body = await request.body()
    except Exception:
        request_body = "<unavailable>"

    request_data["body"] = (
        request_body.decode("utf-8")
        if isinstance(request_body, bytes)
        else request_body
    )

    # Prepare response data, ensuring defaults of 0 for non-nullable fields
    response_data = {
        "status_code": response_status or 0,
    }

    # Ensure error and error_location have default values for non-nullable fields
    error_message = error
    error_location = error_location

    # Log entry creation (replace with actual database logging logic)
    await APIActivityLog.create(
        requesting_ip=requesting_ip or "Unavailable",
        request=request_data,
        response=response_data,
        endpoint_hit=endpoint_hit,
        time_taken=response_time or 0,  # Default to 0 if None
        time_requested=request.state.time_requested,
        time_responded=datetime.now(timezone.utc),
        error=error_message,
        error_location=error_location,
    )


# Middleware class to log API activity and capture response status and time
class APIActivityLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        # Record the time when the request was received
        request.state.time_requested = datetime.now(timezone.utc)

        # Start the timer for response time measurement
        start_time = asyncio.get_event_loop().time()

        try:
            # Call the next middleware or endpoint handler
            response = await call_next(request)

            # Capture response status code and calculate response time in milliseconds
            status_code = response.status_code
            response_time = int(
                (asyncio.get_event_loop().time() - start_time) * 1000
            )  # Convert to milliseconds

            # Log API activity
            await log_api_activity(
                request,
                response_status=status_code,
                response_time=response_time,
            )

        except Exception as e:
            # Log other exceptions with traceback
            error_location = traceback.format_exc()
            await log_api_activity(
                request, error=str(e), error_location=error_location
            )
            raise e

        return response
