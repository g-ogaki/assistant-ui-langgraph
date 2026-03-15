import os
from datetime import datetime
from functools import wraps
from psycopg_pool import AsyncConnectionPool
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel, Field, select
from sqlmodel.ext.asyncio.session import AsyncSession

def with_session(func):
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        if kwargs.get("session") is not None:
            return await func(self, *args, **kwargs)
        
        if any(isinstance(arg, AsyncSession) for arg in args):
            return await func(self, *args, **kwargs)

        async with AsyncSession(self.engine) as session:
            kwargs["session"] = session
            return await func(self, *args, **kwargs)
            
    return wrapper

class ThreadMetadata(SQLModel, table=True):
    """Thread metadata model."""
    thread_id: str = Field(primary_key=True)
    guest_id: str = Field(index=True)
    title: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class ThreadMetadataRepository:
    def __init__(self):
        self.pool = AsyncConnectionPool(
            conninfo=os.getenv("DATABASE_URL"),
            min_size=0,
            max_size=10,
            open=False,
            close_returns=True,
            check=AsyncConnectionPool.check_connection,
            kwargs={
                "prepare_threshold": None,
            },
        )

        self.engine = create_async_engine(
            url="postgresql+psycopg://",
            poolclass=NullPool,
            async_creator=self.pool.getconn,
        )

    async def initialize_database(self):
        await self.pool.open()
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)    
        await self.engine.dispose()
    
    async def terminate_database(self):
        await self.pool.close()

    @with_session
    async def get(self, thread_id: str, guest_id: str, session: AsyncSession = None) -> ThreadMetadata | None:
        result = await session.exec(
            select(ThreadMetadata)
            .where(ThreadMetadata.thread_id == thread_id, ThreadMetadata.guest_id == guest_id)
        )
        return result.first()

    @with_session
    async def get_all(self, guest_id: str, session: AsyncSession = None) -> list[ThreadMetadata]:
        result = await session.exec(
            select(ThreadMetadata)
            .where(ThreadMetadata.guest_id == guest_id)
            .order_by(ThreadMetadata.updated_at.desc())
        )
        return result.all()

    @with_session
    async def create(self, thread_id: str, guest_id: str, title: str, session: AsyncSession = None) -> None:
        thread = ThreadMetadata(thread_id=thread_id, guest_id=guest_id, title=title)
        session.add(thread)
        await session.commit()

    @with_session
    async def update(self, thread_id: str, guest_id: str, session: AsyncSession = None) -> bool:
        thread = await self.get(thread_id, guest_id, session)
        if not thread:
            return False
        thread.updated_at = datetime.now()
        session.add(thread)
        await session.commit()
        return True

    @with_session
    async def delete(self, thread_id: str, guest_id: str, session: AsyncSession = None) -> bool:
        thread = await self.get(thread_id, guest_id, session)
        if not thread:
            return False
        await session.delete(thread)
        await session.commit()
        return True
