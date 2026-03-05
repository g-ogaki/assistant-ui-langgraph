from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from langchain.messages import HumanMessage, SystemMessage

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

def create_graph(checkpointer):
    return create_agent(
        model=llm,
        tools=[multiply],
        system_prompt="You must call the tool 'multiply' if you are requested.",
        checkpointer=checkpointer,
    )

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