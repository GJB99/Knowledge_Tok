import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.backend.models import Content  # Import after sys.path change
from src.backend.database import ARTICLES_DATABASE_URL

async def test_schema():
    engine = create_async_engine(ARTICLES_DATABASE_URL)
    async_session = sessionmaker(engine, class_= AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Try to access the embedding column.  If it exists, this will work.
        # If it doesn't, it will raise an AttributeError.
        try:
            result = await session.execute("SELECT embedding FROM content LIMIT 1")
            print("Embedding column exists.")
        except Exception as e:
            print(f"Error accessing embedding column: {e}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_schema()) 