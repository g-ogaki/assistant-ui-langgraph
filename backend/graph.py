from db import pool, engine
from dotenv import load_dotenv
from typing import Annotated
from pydantic import BaseModel, Field
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

llm = ChatOllama(
    model="gpt-oss:120b-cloud",
    base_url="https://ollama.com", 
)

embeddings = CloudflareWorkersAIEmbeddings(
    model_name="@cf/baai/bge-small-en-v1.5",
)

class AgentState(BaseModel):
    messages: Annotated[list[AnyMessage], add_messages]

# For demonstration; you can simply use langchain.agents.create_agent
async def create_graph():
    vector_store = PGVector(
        embeddings=embeddings,
        embedding_length=384,
        collection_name="IT_help_desk",
        connection=engine,
    )

    retriever = vector_store.as_retriever(search_type="mmr", search_kwargs={"k": 5, "fetch_k": 20})
    retriever_tool = create_retriever_tool(
        retriever=retriever,
        name="knowledge base retriever",
        description="Use this tool to retrieve relevant information from the IT help desk knowledge base."
    )

    tools = [retriever_tool]
    model_with_tools = llm.bind_tools(tools)

    async def model_node(state: AgentState) -> dict:
        response = await model_with_tools.ainvoke([
            SystemMessage(content="""You are a helpful assistant for IT help desk.
            You are given a tool to retrieve knowledge base, so reference it if user asks relevant questions"""),
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

    graph = StateGraph(AgentState)

    graph.add_node("model", model_node)
    graph.add_node("tools", tool_node)

    graph.add_edge(START, "model")
    graph.add_conditional_edges("model", should_continue, ["tools", END])
    graph.add_edge("tools", "model")

    checkpointer = AsyncPostgresSaver(pool)
    await checkpointer.setup()
    return graph.compile(checkpointer=checkpointer)

class ThreadTitle(BaseModel):
    title: str = Field(description="A concise title for the chat thread, maximum 5 words.")

async def generate_title(query: str) -> str:
    structured_llm = llm.with_structured_output(ThreadTitle)
    response = await structured_llm.ainvoke([
        SystemMessage(content="""You are a helpful assistant that generates short, concise titles for chat conversations.
        You must respond ONLY with valid JSON containing a 'title' key."""),
        HumanMessage(content=query)
    ])
    return response.title
