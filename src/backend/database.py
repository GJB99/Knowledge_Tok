import os
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
ARTICLES_DATABASE_URL = os.getenv("ARTICLES_DATABASE_URL", DATABASE_URL)

engine = create_async_engine(DATABASE_URL, future=True, echo=False)
articles_engine = create_async_engine(ARTICLES_DATABASE_URL, future=True, echo=False)

AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
ArticlesSessionLocal = sessionmaker(articles_engine, expire_on_commit=False, class_=AsyncSession)

Base = declarative_base()

async def init_db():
    # Import all models here to ensure they're registered with Base
    from models import Content, User, Interest, Interaction
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def get_articles_db():
    async with ArticlesSessionLocal() as session:
        yield session 