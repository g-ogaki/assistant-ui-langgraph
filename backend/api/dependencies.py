import os
from db import engine
from fastapi import Header, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

SHARED_PROXY_SECRET = os.getenv("SHARED_PROXY_SECRET")

async def verify_proxy_secret(x_proxy_secret: str = Header(None)):
    if x_proxy_secret != SHARED_PROXY_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")

async def require_guest_id(x_guest_id: str = Header(...)):
    if not x_guest_id:
        raise HTTPException(status_code=400, detail="x-guest-id header invalid")
    return x_guest_id
