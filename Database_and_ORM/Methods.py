from tortoise import Tortoise
from tortoise.exceptions import DBConnectionError, ValidationError
from decouple import config
import re

async def init_db():
    try:
        await Tortoise.init(
            db_url=f"{config('DATABASE_URL')}",
            modules={"models": ["Database_and_ORM.Database_Models"]},
        )
        await Tortoise.generate_schemas(safe=True)
    except DBConnectionError as e:
        print("Database connection error:", e)


async def close_db():
    await Tortoise.close_connections()
