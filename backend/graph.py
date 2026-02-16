from langchain_ollama import ChatOllama
from langchain.agents import create_agent

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