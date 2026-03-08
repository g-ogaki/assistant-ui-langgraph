from dotenv import load_dotenv
from typing import Annotated
from pydantic import BaseModel, Field
from langchain_ollama import ChatOllama
from langchain.messages import AIMessage, HumanMessage, SystemMessage, AnyMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt.tool_node import ToolNode

load_dotenv()

def multiply(a: int, b: int) -> int:
    """Calculate the product of two numbers.

    Args:
        a: The first number.
        b: The second number.

    Returns:
        The product of the two numbers.
    """
    return a * b

llm = ChatOllama(
    model="gpt-oss:120b-cloud",
    base_url="https://ollama.com", 
)

class AgentState(BaseModel):
    messages: Annotated[list[AnyMessage], add_messages]

# For demonstration; you can simply use langchain.agents.create_agent
def create_graph(checkpointer):
    tools = [multiply]
    model_with_tools = llm.bind_tools(tools)

    async def model_node(state: AgentState) -> dict:
        response = await model_with_tools.ainvoke([
            SystemMessage(content="You must call the tool 'multiply' if you are requested."),
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