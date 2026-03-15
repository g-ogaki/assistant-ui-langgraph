from db import pool, engine, create_db_and_tables, ThreadMetadata
from utils import langchain_to_vercel_stream
from uuid import uuid4
from dotenv import load_dotenv
from typing import Annotated, Literal, AsyncGenerator
from datetime import datetime
from functools import wraps
from pydantic import BaseModel, Field
from sqlmodel import select, delete
from sqlmodel.ext.asyncio.session import AsyncSession
from langchain_ollama import ChatOllama
from langchain_cloudflare.embeddings import CloudflareWorkersAIEmbeddings
from langchain.messages import AIMessage, HumanMessage, SystemMessage, AnyMessage
from langchain_postgres import PGVector
from langchain_core.tools import create_retriever_tool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt.tool_node import ToolNode
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

load_dotenv()

# Graph definition (just a demonstration; you can simply use langchain.agents.create_agent())
class AgentState(BaseModel):
    messages: Annotated[list[AnyMessage], add_messages]

llm = ChatOllama(
    model="gpt-oss:120b-cloud",
    base_url="https://ollama.com", 
)

embeddings = CloudflareWorkersAIEmbeddings(
    model_name="@cf/baai/bge-small-en-v1.5",
)

vector_store = PGVector(
    embeddings=embeddings,
    embedding_length=384,
    collection_name="IT_help_desk",
    connection=engine,
)

retriever = vector_store.as_retriever(search_type="mmr", search_kwargs={"k": 5, "fetch_k": 20})
retriever_tool = create_retriever_tool(
    retriever=retriever,
    name="knowledge_base_retriever",
    description="Use this tool to retrieve relevant information from the IT help desk knowledge base."
)

tools = [retriever_tool]
model_with_tools = llm.bind_tools(tools)

async def model_node(state: AgentState) -> dict:
    response = await model_with_tools.ainvoke([
        SystemMessage(content="""You are a helpful assistant for the IT help desk.
        You are given a tool to search the knowledge base, so utilize it if users ask relevant questions.
        If the user asks multiple questions, you must reference it for each individual question.
        If you are asked general questions, provide a clear and detailed answer."""),
        *state.messages
    ])
    return {"messages": [response]}

tool_node = ToolNode(tools)

def should_continue(state: AgentState) -> str:
    """If the last message has tool calls, route to 'tools'; otherwise end."""
    last_message = state.messages[-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"
    return END

graph_builder = StateGraph(AgentState)

graph_builder.add_node("model", model_node)
graph_builder.add_node("tools", tool_node)

graph_builder.add_edge(START, "model")
graph_builder.add_conditional_edges("model", should_continue, ["tools", END])
graph_builder.add_edge("tools", "model")

# Agent definition
def with_session(func):
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        async with AsyncSession(engine) as session:
            return await func(self, *args, session=session, **kwargs)
    return wrapper

class ThreadTitle(BaseModel):
    title: str = Field(description="A concise title for the chat thread, maximum 5 words.")

class Message(BaseModel):
    type: Literal["human", "ai", "tool"]
    content: str
    id: str | None = None
    tool_call_id: str | None = None
    name: str | None = None
    args: dict | None = None
    output: str | None = None

class Agent:
    def __init__(self):
        self.graph = None

    async def initialize(self):
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()
        await create_db_and_tables()
        self.graph = graph_builder.compile(checkpointer=checkpointer)
    
    async def _generate_title(self, query: str) -> str:
        structured_llm = llm.with_structured_output(ThreadTitle)
        response = await structured_llm.ainvoke([
            SystemMessage(content="""You are a helpful assistant that generates short, concise titles for chat conversations.
            You must respond ONLY with valid JSON containing a 'title' key."""),
            HumanMessage(content=query)
        ])
        return response.title
    
    async def _get_thread(self, thread_id: str, x_guest_id: str, session: AsyncSession) -> ThreadMetadata | None:
        result = await session.exec(select(ThreadMetadata).where(ThreadMetadata.thread_id == thread_id, ThreadMetadata.guest_id == x_guest_id))
        return result.first()

    @with_session
    async def get_threads(self, x_guest_id: str, session: AsyncSession = None) -> list[ThreadMetadata]:
        result = await session.exec(select(ThreadMetadata).where(ThreadMetadata.guest_id == x_guest_id).order_by(ThreadMetadata.updated_at.desc()))
        return result.all()

    @with_session
    async def create_thread(self, x_guest_id: str, query: str, session: AsyncSession = None) -> str:
        thread_id = str(uuid4())
        title = await self._generate_title(query)
        session.add(ThreadMetadata(thread_id=thread_id, guest_id=x_guest_id, title=title))
        await session.commit()
        return thread_id
    
    @with_session
    async def update_thread(self, thread_id: str, x_guest_id: str, session: AsyncSession = None) -> bool:
        thread = await self._get_thread(thread_id, x_guest_id, session)
        if not thread:
            return False
        thread.updated_at = datetime.now()
        await session.commit()
        return True
            
    @with_session
    async def delete_thread(self, thread_id: str, x_guest_id: str, session: AsyncSession = None) -> bool:
        thread = await self._get_thread(thread_id, x_guest_id, session)
        if not thread:
            return False
        await session.delete(thread)
        await session.commit()
        return True
    
    @with_session
    async def get_messages(self, thread_id: str, x_guest_id: str, session: AsyncSession = None) -> list[Message] | None:
        if not await self._get_thread(thread_id, x_guest_id, session):
            return None
        state = await self.graph.aget_state(config={"configurable": {"thread_id": thread_id}})
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
        return messages
    
    @with_session
    async def invoke(self, thread_id: str, x_guest_id: str, query: str, session: AsyncSession = None) -> AsyncGenerator[str, None] | None:
        if not await self._get_thread(session, thread_id, x_guest_id):
            return None
        astream_events = self.graph.astream_events(
            input={"messages": HumanMessage(content=query)},
            config={"configurable": {"thread_id": thread_id}}
        )
        return langchain_to_vercel_stream(astream_events)
