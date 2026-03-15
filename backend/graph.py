from utils import langchain_to_vercel_stream
from typing import Annotated, Literal, AsyncGenerator
from psycopg_pool import AsyncConnectionPool
from sqlalchemy.ext.asyncio import AsyncEngine
from pydantic import BaseModel, Field
from langchain.messages import AIMessage, HumanMessage, SystemMessage, AnyMessage
from langchain_core.runnables import Runnable
from langchain_core.tools import create_retriever_tool
from langchain_ollama import ChatOllama
from langchain_cloudflare.embeddings import CloudflareWorkersAIEmbeddings
from langchain_postgres import PGVector
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt.tool_node import ToolNode
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

# Graph definition (just a demonstration; you can simply use langchain.agents.create_agent())
class AgentState(BaseModel):
    messages: Annotated[list[AnyMessage], add_messages]

def get_graph_builder(llm: Runnable, embeddings: Runnable, engine: AsyncEngine):
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

    return graph_builder

# Agent definition
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
        self.llm = ChatOllama(
            model="gpt-oss:120b-cloud",
            base_url="https://ollama.com", 
        )
        self.embeddings = CloudflareWorkersAIEmbeddings(
            model_name="@cf/baai/bge-small-en-v1.5",
        )
        self.graph = None

    async def initialize_graph(self, pool: AsyncConnectionPool, engine: AsyncEngine):
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()
        graph_builder = get_graph_builder(self.llm, self.embeddings, engine)
        self.graph = graph_builder.compile(checkpointer=checkpointer)
    
    async def generate_title(self, query: str) -> str:
        structured_llm = self.llm.with_structured_output(ThreadTitle)
        response = await structured_llm.ainvoke([
            SystemMessage(content="""You are a helpful assistant that generates short, concise titles for chat conversations.
            You must respond ONLY with valid JSON containing a 'title' key."""),
            HumanMessage(content=query)
        ])
        return response.title
    
    async def get_messages(self, thread_id: str) -> list[Message] | None:
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
    
    async def stream(self, thread_id: str, query: str) -> AsyncGenerator[str, None] | None:
        astream_events = self.graph.astream_events(
            input={"messages": HumanMessage(content=query)},
            config={"configurable": {"thread_id": thread_id}}
        )
        return langchain_to_vercel_stream(astream_events)
