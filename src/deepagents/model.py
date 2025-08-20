import os
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI


def get_default_model() -> object:
    """Return the default chat model for deepagents.

    Select provider via env var `DEEPAGENTS_MODEL_PROVIDER`:
    - "ollama" (default): uses langchain-ollama ChatOllama
    - "lm-studio": uses langchain-openai ChatOpenAI with LM‑Studio's OpenAI-compatible API
    """
    provider = os.getenv("DEEPAGENTS_MODEL_PROVIDER", "ollama").lower()

    if provider in {"lm-studio", "lmstudio"}:
        # LM‑Studio (OpenAI-compatible) configuration
        base_url = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
        api_key = os.getenv("LM_STUDIO_API_KEY", "lm-studio")  # LM‑Studio ignores the key
        model = os.getenv("LM_STUDIO_MODEL_NAME", "local-model")
        # Pass max_tokens only for OpenAI-compatible providers
        return ChatOpenAI(model=model, base_url=base_url, api_key=api_key, max_tokens=64000)

    # Default to Ollama local model
    ollama_model = os.getenv("OLLAMA_MODEL_NAME", "qwen3:4b-thinking-2507-q4_K_M")
    # Accept either OLLAMA_BASE_URL or OLLAMA_HOST
    base_url = os.getenv("OLLAMA_BASE_URL") or os.getenv("OLLAMA_HOST")
    kwargs = {"model": ollama_model}
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOllama(**kwargs)
