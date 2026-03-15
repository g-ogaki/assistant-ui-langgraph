from db import ThreadMetadata, ThreadMetadataRepository
from graph import Agent, Message
from uuid import uuid4
from typing import AsyncGenerator

class ChatService:
    def __init__(self):
        self.repository = ThreadMetadataRepository() 
        self.agent = Agent()

    async def startup(self):
        await self.repository.initialize_database()
        await self.agent.initialize_graph(self.repository.pool, self.repository.engine)
    
    async def shutdown(self):
        await self.repository.terminate_database()
    
    async def get_threads(self, x_guest_id: str) -> list[ThreadMetadata]:
        return await self.repository.get_all(x_guest_id)
    
    async def create_thread(self, x_guest_id: str, query: str) -> str:
        thread_id = str(uuid4())
        title = await self.agent.generate_title(query)
        await self.repository.create(thread_id, x_guest_id, title)
        return thread_id
    
    async def update_thread(self, thread_id: str, x_guest_id: str) -> bool:
        return await self.repository.update(thread_id, x_guest_id)
    
    async def delete_thread(self, thread_id: str, x_guest_id: str) -> bool:
        return await self.repository.delete(thread_id, x_guest_id)
    
    async def get_messages(self, thread_id: str, x_guest_id: str) -> list[Message] | None:
        if not self.repository.get(thread_id, x_guest_id):
            return None
        return await self.agent.get_messages(thread_id)
    
    async def stream(self, thread_id: str, x_guest_id: str, query: str) -> AsyncGenerator[str, None] | None:
        if not self.repository.get(thread_id, x_guest_id):
            return None
        return await self.agent.stream(thread_id, query)
