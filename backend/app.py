import os
from dotenv import load_dotenv
from db import pool, engine, create_db_and_tables, ThreadMetadata
from graph import create_graph, generate_title
from utils import langchain_to_vercel_stream
from uuid import uuid4
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Literal
from fastapi import FastAPI, Header, APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import SQLModel, select, delete
from sqlmodel.ext.asyncio.session import AsyncSession
from langchain.messages import HumanMessage

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await pool.open()
    await create_db_and_tables()
    app.state.agent = await create_graph()

    yield

    await pool.close()

app = FastAPI(lifespan=lifespan)

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

async def require_guest_id(x_guest_id: str = Header(...)):
    if not x_guest_id:
        raise HTTPException(status_code=400, detail="x-guest-id header invalid")
    return x_guest_id

async def get_session():
    async with AsyncSession(engine) as session:
        yield session

@app.api_route("/", methods=["GET", "HEAD"])
def health_check():
    return {"status": "ok"}

@app.get("/api/threads", response_model=GetThreadsResponse)
async def get_threads(x_guest_id: str = Depends(require_guest_id), session: AsyncSession = Depends(get_session)):
    threads = await session.exec(select(ThreadMetadata).where(ThreadMetadata.guest_id == x_guest_id).order_by(ThreadMetadata.updated_at.desc()))
    return GetThreadsResponse(threads=[
        ThreadInfo(
            thread_id=thread.thread_id,
            title=thread.title
        ) for thread in threads
    ])

@app.post("/api/threads", response_model=PostThreadsResponse)
async def create_thread(request: PostThreadRequest, x_guest_id: str = Depends(require_guest_id), session: AsyncSession = Depends(get_session)):
    thread_id = str(uuid4())
    title = await generate_title(request.query)
    thread_metadata = ThreadMetadata(thread_id=thread_id, guest_id=x_guest_id, title=title)
    session.add(thread_metadata)
    await session.commit()
    return PostThreadsResponse(thread_id=thread_id)

@app.put("/api/threads/{thread_id}")
async def update_thread(thread_id: str, request: Request, x_guest_id: str = Depends(require_guest_id), session: AsyncSession = Depends(get_session)):
    thread = await session.get(ThreadMetadata, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    thread.updated_at = datetime.now()
    await session.commit()
    return {"status": "ok"}

@app.delete("/api/threads/{thread_id}")
async def delete_thread(request: Request, thread_id: str, x_guest_id: str = Depends(require_guest_id), session: AsyncSession = Depends(get_session)):
    agent = request.app.state.agent
    await agent.checkpointer.adelete_thread(thread_id)
    await session.execute(delete(ThreadMetadata).where(ThreadMetadata.thread_id == thread_id))
    await session.commit()
    return {"status": "ok"}

@app.get("/api/threads/{thread_id}/messages", response_model=GetMessagesResponse)
async def get_messages(request: Request, thread_id: str, x_guest_id: str = Depends(require_guest_id)):
    agent = request.app.state.agent
    state = await agent.aget_state(config={"configurable": {"thread_id": thread_id}})
    messages = []
    tool_calls = {}
    for msg in state.values.get("messages", []):
        if msg.type == "ai" and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls[tc["id"]] = tc
        elif msg.type == "tool":
            if msg.tool_call_id in tool_calls:
                tc = tool_calls.pop(msg.tool_call_id)
                messages.append(Message(type="tool", content="", id=msg.id, tool_call_id=msg.tool_call_id, name=tc["name"], args=tc["args"], output=msg.content))
        else:
            messages.append(Message(type=msg.type, content=msg.content, id=msg.id))
    return GetMessagesResponse(messages=messages)

@app.post("/api/threads/{thread_id}/messages")
async def chat_endpoint(request: Request, thread_id: str, request_body: PostMessagesRequest, x_guest_id: str = Depends(require_guest_id)):
    agent = request.app.state.agent
    astream_events = agent.astream_events(
        input={"messages": HumanMessage(content=request_body.query)},
        config={"configurable": {"thread_id": thread_id}}
    )
    return StreamingResponse(
        langchain_to_vercel_stream(astream_events),
        media_type="text/event-stream",
        headers={
            "x-vercel-ai-ui-message-stream": "v1",
        },
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
