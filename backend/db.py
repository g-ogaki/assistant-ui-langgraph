import os
from dotenv import load_dotenv
import asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel, Field

load_dotenv()

class ThreadMetadata(SQLModel, table=True):
    """Thread metadata model."""

    thread_id: str = Field(primary_key=True)
    guest_id: str = Field(index=True)
    title: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

url = os.getenv("DATABASE_URL").replace("postgresql://", "postgresql+asyncpg://").replace("?sslmode=require", "")
engine = create_async_engine(
    url,
    connect_args={"ssl": True},
    pool_pre_ping=True,
    pool_size=0,
    max_overflow=5,
    pool_recycle=300,
)

async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(create_db_and_tables())