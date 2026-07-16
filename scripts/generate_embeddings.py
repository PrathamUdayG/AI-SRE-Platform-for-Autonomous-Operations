import asyncio
import sys


async def main():
    print("Pre-populating vector database with SRE documentation...")
    # Embedding generation logic goes here
    print("Embedding generation complete.")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
