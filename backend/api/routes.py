from db import ThreadMetadata
from graph import generate_title
from utils import langchain_to_vercel_stream
from api.schemas import (
    Message,
    ThreadInfo,
    GetThreadsResponse,
    PostThreadRequest,
    PostThreadsResponse,
    GetMessagesResponse,
    PostMessagesRequest
)
from api.dependencies import verify_proxy_secret, require_guest_id, get_session
from uuid import uuid4
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlmodel import select, delete
from sqlmodel.ext.asyncio.session import AsyncSession
from langchain.messages import HumanMessage

api_router = APIRouter(
    prefix="/api",
    dependencies=[Depends(verify_proxy_secret)]
)

@api_router.get("/threads", response_model=GetThreadsResponse)
async def get_threads(x_guest_id: str = Depends(require_guest_id), session: AsyncSession = Depends(get_session)):
    threads = await session.exec(select(ThreadMetadata).where(ThreadMetadata.guest_id == x_guest_id).order_by(ThreadMetadata.updated_at.desc()))
    return GetThreadsResponse(threads=[
        ThreadInfo(thread_id=thread.thread_id, title=thread.title) for thread in threads
    ])

@api_router.post("/threads", response_model=PostThreadsResponse)
async def create_thread(request: PostThreadRequest, x_guest_id: str = Depends(require_guest_id), session: AsyncSession = Depends(get_session)):
    thread_id = str(uuid4())
    title = await generate_title(request.query)
    thread_metadata = ThreadMetadata(thread_id=thread_id, guest_id=x_guest_id, title=title)
    session.add(thread_metadata)
    await session.commit()
    return PostThreadsResponse(thread_id=thread_id)

@api_router.put("/threads/{thread_id}")
async def update_thread(thread_id: str, request: Request, x_guest_id: str = Depends(require_guest_id), session: AsyncSession = Depends(get_session)):
    thread = await session.get(ThreadMetadata, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    thread.updated_at = datetime.now()
    await session.commit()
    return {"status": "ok"}

@api_router.delete("/threads/{thread_id}")
async def delete_thread(request: Request, thread_id: str, x_guest_id: str = Depends(require_guest_id), session: AsyncSession = Depends(get_session)):
    agent = request.app.state.agent
    await agent.checkpointer.adelete_thread(thread_id)
    await session.execute(delete(ThreadMetadata).where(ThreadMetadata.thread_id == thread_id))
    await session.commit()
    return {"status": "ok"}

@api_router.get("/threads/{thread_id}/messages", response_model=GetMessagesResponse)
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

@api_router.post("/threads/{thread_id}/messages")
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
