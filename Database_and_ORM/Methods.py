from tortoise import Tortoise
from tortoise.exceptions import DBConnectionError
from decouple import config
from urllib.parse import urlparse

async def init_db():
    try:
        # Parse DATABASE_URL
        url = urlparse(config("DATABASE_URL"))
       
        # Extract credentials
        db_config = {
            "host": url.hostname,
            "port": url.port,
            "user": url.username,
            "password": url.password,
            "database": url.path.lstrip("/"),  # remove leading /
            "maxsize": 5,  # max pool size
        }

        await Tortoise.init(
            config={
                "connections": {
                    "default": {
                        "engine": "tortoise.backends.asyncpg",
                        "credentials": db_config,
                    }
                },
                "apps": {
                    "models": {
                        "models": ["Database_and_ORM.Database_Models"],
                        "default_connection": "default",
                    }
                },
            }
        )
        await Tortoise.generate_schemas(safe=True)
    except DBConnectionError as e:
        print("Database connection error:", e)

async def close_db():
    await Tortoise.close_connections()