from Database_and_ORM.Methods import init_db, close_db
from Database_and_ORM.Database_Models import APIActivityLog
from datetime import datetime, timezone
from fastapi import Request
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from decouple import config
from typing import Optional, Callable
from time import perf_counter
import asyncio
import traceback


API_KEY = config("API_KEY")
EXCLUDED_PATHS = {
    path.strip()
    for path in config("EXCLUDED_PATHS", default="").split(",")
    if path.strip()
}

_API_LOG_WRITE_LIMIT = asyncio.Semaphore(8)


async def startup_event():
    await init_db()


async def shutdown_event():
    await close_db()


class VerifyAPIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        """
        Checks API key without repeatedly reading env config per request.
        FE-facing behaviour stays the same.
        """
        if request.url.path in EXCLUDED_PATHS:
            return await call_next(request)

        api_key = request.headers.get("API-KEY")

        if not api_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "No API key present"},
            )

        if api_key != API_KEY:
            return JSONResponse(
                status_code=403,
                content={"detail": "Invalid API Key"},
            )

        return await call_next(request)


def _safe_text(value) -> str:
    try:
        return str(value)
    except Exception:
        return "Unserializable error"


async def _write_api_activity_log(
    *,
    endpoint_hit: str,
    requesting_ip: str,
    request_data: dict,
    response_status: Optional[int],
    response_time: Optional[int],
    time_requested: datetime,
    error: Optional[str] = None,
    error_location: Optional[str] = None,
):
    """
    Writes API activity without being on the response hot path.
    Any logging failure is swallowed because logging must not break user/API behaviour.
    """
    try:
        async with _API_LOG_WRITE_LIMIT:
            await APIActivityLog.create(
                requesting_ip=requesting_ip or "Unavailable",
                request=request_data,
                response={"status_code": response_status or 0},
                endpoint_hit=endpoint_hit,
                time_taken=response_time or 0,
                time_requested=time_requested,
                time_responded=datetime.now(timezone.utc),
                error=error,
                error_location=error_location,
            )
    except Exception:
        # Logging is internal. Never let it change API behaviour.
        pass


def _schedule_api_activity_log(**kwargs):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return

    task = loop.create_task(_write_api_activity_log(**kwargs))

    def _consume_task_exception(done_task: asyncio.Task):
        try:
            done_task.result()
        except Exception:
            pass

    task.add_done_callback(_consume_task_exception)


class APIActivityLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        time_requested = datetime.now(timezone.utc)
        start_time = perf_counter()

        endpoint_hit = request.url.path
        requesting_ip = request.client.host if request.client else "Unavailable"
        request_data = {
            "headers": dict(request.headers),
            "user_agent": request.headers.get("User-Agent"),
            "body": "<not captured on response hot path>",
        }

        try:
            response = await call_next(request)

            response_time = int((perf_counter() - start_time) * 1000)

            _schedule_api_activity_log(
                endpoint_hit=endpoint_hit,
                requesting_ip=requesting_ip,
                request_data=request_data,
                response_status=response.status_code,
                response_time=response_time,
                time_requested=time_requested,
            )

            return response

        except Exception as e:
            response_time = int((perf_counter() - start_time) * 1000)

            _schedule_api_activity_log(
                endpoint_hit=endpoint_hit,
                requesting_ip=requesting_ip,
                request_data=request_data,
                response_status=500,
                response_time=response_time,
                time_requested=time_requested,
                error=_safe_text(e),
                error_location=traceback.format_exc(limit=2),
            )

            raise