# Assistant UI + Python LangGraph

A full-stack monorepo integrating a modern chat interface built with [assistant-ui](https://github.com/assistant-ui/assistant-ui) on the frontend and [LangGraph](https://langchain-ai.github.io/langgraph/) and [FastAPI](https://fastapi.tiangolo.com/) on the backend.

## Getting Started

You can try this application on [https://assistant-ui-langgraph.monipy.workers.dev](https://assistant-ui-langgraph.monipy.workers.dev){:target="_blank"}

### Architecture

* **Frontend**: Next.js hosted on [Cloudflare Workers](https://workers.cloudflare.com/)
* **Backend**: FastAPI serving a LangGraph agent hosted on [Render](https://render.com/) in combination with [UptimeRobot](https://uptimerobot.com/) to keep it awake
* **Database**: PostgreSQL on [Neon](https://neon.com/) for thread management, LangGraph's checkpointer, and vector store for RAG

## For Developers

See the individual component READMEs for detailed setup instructions and local development:

* [**Frontend Documentation**](frontend/README.md)
* [**Backend Documentation**](backend/README.md)

## License

All original code, scripts, and documentation in this repository are dedicated to the public domain under the [CC0 1.0 Universal License](LICENSE).

### Third-Party Licenses

This project relies on open-source software and data. Components including but not limited to the following are not covered by CC0 and remain under their respective **MIT Licenses**:

* **[assistant-ui](https://github.com/assistant-ui/assistant-ui)**: Used for the React frontend interface. (MIT License)
* **[LangChain](https://github.com/langchain-ai/langchain)**: Used for the backend LLM orchestration. (MIT License)
* **[Sample RAG Knowledge Item Dataset](https://www.kaggle.com/datasets/dkhundley/sample-rag-knowledge-item-dataset)**: The sample dataset located in the `backend/preprocess/data` directory. See the dedicated [README.md](backend/preprocess/data/README.md) for the original copyright notice. (MIT License)
