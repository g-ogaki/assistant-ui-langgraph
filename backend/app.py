from service import ChatService
from api.routes import api_router
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.service = ChatService()
    await app.state.service.startup()
    yield
    await app.state.service.shutdown()

app = FastAPI(lifespan=lifespan)

@app.api_route("/", methods=["GET", "HEAD"])
def health_check():
    return {"status": "ok"}

app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    from dotenv import load_dotenv
    load_dotenv()
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
