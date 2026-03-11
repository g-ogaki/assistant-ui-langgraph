from typing import Literal
from pydantic import BaseModel

class Message(BaseModel):
    type: Literal["human", "ai", "tool"]
    content: str
    id: str | None = None
    tool_call_id: str | None = None
    name: str | None = None
    args: dict | None = None
    output: str | None = None

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
