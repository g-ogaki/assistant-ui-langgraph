import os
from dotenv import load_dotenv
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
from psycopg_pool import AsyncConnectionPool
from sqlmodel import SQLModel, Field

load_dotenv()

class ThreadMetadata(SQLModel, table=True):
    """Thread metadata model."""
    thread_id: str = Field(primary_key=True)
    guest_id: str = Field(index=True)
    title: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

pool = AsyncConnectionPool(
    conninfo=os.getenv("DATABASE_URL"),
    min_size=0,
    max_size=10,
    open=False,
    close_returns=True,
    check=AsyncConnectionPool.check_connection,
    kwargs={
        "prepare_threshold": 0,
    },
)

engine = create_async_engine(
    url="postgresql+psycopg://",
    poolclass=NullPool,
    async_creator=pool.getconn,
)
