from dotenv import load_dotenv
from contextlib import asynccontextmanager
from fastapi import FastAPI
from db import pool, create_db_and_tables
from graph import create_graph
from api.routes import api_router

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await pool.open()
    await create_db_and_tables()
    app.state.agent = await create_graph()
    yield
    await pool.close()

app = FastAPI(lifespan=lifespan)

@app.api_route("/", methods=["GET", "HEAD"])
def health_check():
    return {"status": "ok"}

app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
