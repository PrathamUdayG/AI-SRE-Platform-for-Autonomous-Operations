import asyncio
import sys

from src.infrastructure.config import settings


async def init_db():
    print(f"Initializing database at: {settings.DATABASE_URL}")
    # Database initialization logic would go here
    print("Database initialization complete.")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(init_db())
