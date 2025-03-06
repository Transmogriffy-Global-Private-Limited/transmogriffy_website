# main.py
from fastapi import FastAPI
from Database_and_ORM.Database_Connector import init_db, close_db
from Users.Router import User_Router
from Admin.Router import Admin_Router
from Products.Router import Products_Router
from decouple import config
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware import Middleware
from fastapi.responses import FileResponse
from Methods import VerifyAPIKeyMiddleware, APIActivityLoggingMiddleware
from contextlib import asynccontextmanager
from os import path


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
        expose_headers=["Authorization", "authorization"],
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
    (Products_Router, "/products", ["Products"])
]

for router, prefix, tags in routers:
    app.include_router(router, prefix=prefix, tags=tags)
