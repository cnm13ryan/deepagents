# from langchain_anthropic import ChatAnthropic
from langchain_ollama import ChatOllama


def get_default_model():
    # return ChatAnthropic(model_name="claude-sonnet-4-20250514", max_tokens=64000)
    return ChatOllama(model="ollama:qwen3:4b-thinking-2507-q4_K_M", max_tokens=64000)
