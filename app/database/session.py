import os
from dotenv import load_dotenv
from app.core.config import settings

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base, sessionmaker
load_dotenv()

DATABASE_URL = (
    f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}"
    f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
)


engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = async_sessionmaker(engine, autocommit=False, autoflush=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def get_db_session():
    async with AsyncSessionLocal() as session:
        return session