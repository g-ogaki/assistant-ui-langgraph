from graph import Message
from pydantic import BaseModel

class ThreadInfo(BaseModel):
    thread_id: str
    title: str

class GetThreadsResponse(BaseModel):
    threads: list[ThreadInfo]

class PostThreadRequest(BaseModel):
    query: str | list[dict]

class PostThreadsResponse(BaseModel):
    thread_id: str

class GetMessagesResponse(BaseModel):
    messages: list[Message]

class PostMessagesRequest(BaseModel):
    query: str | list[dict]
