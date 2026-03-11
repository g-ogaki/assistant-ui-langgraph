# LangGraph Backend

This is the backend service for the Assistant UI project, exposing a RAG agent via FastAPI and LangGraph.

## Features

* **FastAPI**: Provides REST APIs and server-sent events (SSE) streaming endpoints for real-time chat messages.
* **LangGraph Agent**: Orchestrates the RAG interactions, incorporating tool usage.
* **Vercel AI SDK Support**: Translates LangChain's astream_events to follow [Data Transfer Protocol](https://ai-sdk.dev/docs/ai-sdk-ui/stream-protocol#data-stream-protocol) in `utils.py`.
* **Ollama Integration**: Employs `langchain-ollama` for LLM inference (e.g., `gpt-oss:120b-cloud`).
* **Vector Retrieval (RAG)**: Integrates PGVector and Cloudflare Workers AI embeddings (`@cf/baai/bge-small-en-v1.5`) to search an IT Help Desk Knowledge Base.
* **Persistent State**: Stores conversation histories, checkpoints, and thread metadata natively using PostgreSQL (`langgraph-checkpoint-postgres` and SQLModel).

## Prerequisites

* Python 3.10+
* PostgreSQL Database

## Getting Started

1. Set up a virtual environment and install dependencies:
   ```bash
   uv venv
   uv pip install -r requirements.txt
   ```

2. Configure your environment variables.
   Copy the `.env.example` to `.env` and fill in the required keys (database connection string, proxy secrets, API keys, etc).

3. Start the FastAPI server:
   ```bash
   uv run app.py
   ```
   The API will be accessible at `http://localhost:8000`.