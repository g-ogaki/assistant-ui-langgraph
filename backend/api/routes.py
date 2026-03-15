from api.schemas import (
    ThreadInfo,
    GetThreadsResponse,
    PostThreadRequest,
    PostThreadsResponse,
    GetMessagesResponse,
    PostMessagesRequest
)
from api.dependencies import verify_proxy_secret, require_guest_id
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

api_router = APIRouter(
    prefix="/api",
    dependencies=[Depends(verify_proxy_secret)]
)

@api_router.get("/threads", response_model=GetThreadsResponse)
async def get_threads(request: Request, x_guest_id: str = Depends(require_guest_id)):
    threads = await request.app.state.agent.get_threads(x_guest_id)
    return GetThreadsResponse(threads=[
        ThreadInfo(thread_id=thread.thread_id, title=thread.title) for thread in threads
    ])

@api_router.post("/threads", response_model=PostThreadsResponse)
async def create_thread(request: Request, request_body: PostThreadRequest, x_guest_id: str = Depends(require_guest_id)):
    thread_id = await request.app.state.agent.create_thread(x_guest_id, request_body.query)
    return PostThreadsResponse(thread_id=thread_id)

@api_router.put("/threads/{thread_id}")
async def update_thread(request: Request, thread_id: str, x_guest_id: str = Depends(require_guest_id)):
    response = await request.app.state.agent.update_thread(thread_id, x_guest_id)
    if not response:
        raise HTTPException(status_code=404, detail="Thread not found")
    return {"status": "ok"}

@api_router.delete("/threads/{thread_id}")
async def delete_thread(request: Request, thread_id: str, x_guest_id: str = Depends(require_guest_id)):
    response = await request.app.state.agent.delete_thread(thread_id, x_guest_id)
    if not response:
        raise HTTPException(status_code=404, detail="Thread not found")
    return {"status": "ok"}

@api_router.get("/threads/{thread_id}/messages", response_model=GetMessagesResponse)
async def get_messages(request: Request, thread_id: str, x_guest_id: str = Depends(require_guest_id)):
    messages = await request.app.state.agent.get_messages(thread_id, x_guest_id)
    if messages is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    return GetMessagesResponse(messages=messages)

@api_router.post("/threads/{thread_id}/messages")
async def invoke(request: Request, request_body: PostMessagesRequest, thread_id: str, x_guest_id: str = Depends(require_guest_id)):
    async_stream = await request.app.state.agent.invoke(thread_id, x_guest_id, request_body.query)
    if async_stream is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    return StreamingResponse(
        async_stream,
        media_type="text/event-stream",
        headers={
            "x-vercel-ai-ui-message-stream": "v1",
        },
    )
