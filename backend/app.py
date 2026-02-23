from uuid import uuid4
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from graph import create_graph
from db import engine, ThreadMetadata
from utils import langchain_to_vercel_stream
from fastapi import FastAPI, Header, APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from pydantic import BaseModel
from sqlmodel import select, delete
from sqlmodel.ext.asyncio.session import AsyncSession
from contextlib import asynccontextmanager
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncSqliteSaver.from_conn_string("sqlite.db") as checkpointer:
        app.state.agent = create_graph(checkpointer)
        yield

app = FastAPI(lifespan=lifespan)

class Message(BaseModel):
    type: str
    content: str | list[dict]
    id: str | None = None

class ThreadInfo(BaseModel):
    thread_id: str
    title: str
    created_at: str

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

class PatchThreadRequest(BaseModel):
    title: str

async def require_guest_id(x_guest_id: str = Header(...)):
    if not x_guest_id:
        raise HTTPException(status_code=400, detail="x-guest-id header invalid")
    return x_guest_id

async def get_session():
    async with AsyncSession(engine) as session:
        yield session

@app.get("/")
def health_check():
    return {"status": "ok"}

@app.get("/api/threads")
async def get_threads(x_guest_id: str = Depends(require_guest_id), session: AsyncSession = Depends(get_session)):
    threads = await session.exec(select(ThreadMetadata).where(ThreadMetadata.guest_id == x_guest_id).order_by(ThreadMetadata.created_at.desc()))
    return GetThreadsResponse(threads=[
        ThreadInfo(
            thread_id=thread.thread_id,
            title=thread.title,
            created_at=thread.created_at.isoformat(),
        )
        for thread in threads
    ])

@app.post("/api/threads", response_model=PostThreadsResponse)
async def create_thread(request: PostThreadRequest, x_guest_id: str = Depends(require_guest_id), session: AsyncSession = Depends(get_session)):
    thread_id = str(uuid4())
    thread_metadata = ThreadMetadata(thread_id=thread_id, guest_id=x_guest_id, title=request.query)
    session.add(thread_metadata)
    await session.commit()
    return PostThreadsResponse(thread_id=thread_id)

@app.patch("/api/threads/{thread_id}")
async def rename_thread(thread_id: str, request: PatchThreadRequest, x_guest_id: str = Depends(require_guest_id), session: AsyncSession = Depends(get_session)):
    thread = await session.get(ThreadMetadata, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    thread.title = request.title
    session.add(thread)
    await session.commit()
    return {"status": "ok"}

@app.delete("/api/threads/{thread_id}")
async def delete_thread(request: Request, thread_id: str, x_guest_id: str = Depends(require_guest_id), session: AsyncSession = Depends(get_session)):
    agent = request.app.state.agent
    agent.checkpointer.adelete_thread(thread_id)
    await session.execute(delete(ThreadMetadata).where(ThreadMetadata.thread_id == thread_id))
    await session.commit()
    return {"status": "ok"}

@app.get("/api/threads/{thread_id}/messages", response_model=GetMessagesResponse)
async def get_messages(request: Request, thread_id: str, x_guest_id: str = Depends(require_guest_id)):
    agent = request.app.state.agent
    state = await agent.aget_state(config={"configurable": {"thread_id": thread_id}})
    messages = []
    for msg in state.values.get("messages", []):
        if isinstance(msg, HumanMessage):
            messages.append(Message(type="human", content=msg.content, id=msg.id))
        elif isinstance(msg, AIMessage):
            messages.append(Message(type="ai", content=msg.content, id=msg.id))
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