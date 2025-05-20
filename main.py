# main.py
from fastapi import FastAPI
from Database_and_ORM.Database_Connector import init_db, close_db
from Users.Router import User_Router
from Admin.Router import Admin_Router
from Products.Router import Products_Router
from Cart.Router import cart_router
from decouple import config
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware import Middleware
from fastapi.responses import FileResponse
from Methods import VerifyAPIKeyMiddleware, APIActivityLoggingMiddleware
from contextlib import asynccontextmanager
from os import path
from Order.Router import order_router
from Payments.Router import payment_router
from Contactus.Router import contact_router
from Analytics.Router import analytics_router
from BuyNow.Router import buynow_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run startup code here
    await init_db()
    yield
    # Run shutdown code here
    await close_db()


middlewares = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allows all origins; customize as needed
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[
            "Authorization",
            "authorization",
            "User_Type",
            "user_type",
            "User_type",
            "Two_Factor_Enabled",
            "two_factor_enabled",
        ],
    ),
    Middleware(VerifyAPIKeyMiddleware),
    Middleware(APIActivityLoggingMiddleware),
]

app = FastAPI(
    title="Transmogriffy_Website_Backend",
    lifespan=lifespan,
    middleware=middlewares,
)


# Global route
@app.get("/")
async def root():
    return {"message": "Welcome to the Transmogriffy Website Backend"}


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Serves the default favicon.ico."""
    if path.exists(config("FAVICON_PATH")):
        return FileResponse(config("FAVICON_PATH"))


# Register the routers
routers = [
    (User_Router, "/users", ["Users"]),
    (Admin_Router, "/admin", ["Admin"]),
    (Products_Router, "/products", ["Products"]),
    (cart_router, "/cart", ["Cart"]),
    (order_router, "/order", ["Order"]),
    (payment_router, "/payments", ["Payments"]),
    (contact_router,'/contact',['ContactUs']),
    (analytics_router,'/analytics',['Analytics']),
    (buynow_router,'/buynow',['BuyNow'])
]

for router, prefix, tags in routers:
    app.include_router(router, prefix=prefix, tags=tags)

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import traceback

def safe_serialize(obj):
    try:
        return str(obj)
    except Exception:
        return "Unserializable error"

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    print (exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": safe_serialize(exc.detail)},
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "detail": safe_serialize(exc),
            "trace": traceback.format_exc(limit=2),
        },
    )