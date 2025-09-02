import os


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
        try:
            from langchain_openai import ChatOpenAI  # lazy import
            return ChatOpenAI(model=model, base_url=base_url, api_key=api_key, max_tokens=64000)
        except Exception:
            class _ChatOpenAIStub:
                def __init__(self, model: str, base_url: str, api_key: str, max_tokens: int | None = None):
                    self.model = model
                    self.base_url = base_url
                    self.api_key = api_key
                    self.max_tokens = max_tokens

            return _ChatOpenAIStub(model=model, base_url=base_url, api_key=api_key, max_tokens=64000)

    # Default to Ollama local model
    ollama_model = os.getenv("OLLAMA_MODEL_NAME", "qwen3:4b-thinking-2507-q4_K_M")
    # Accept either OLLAMA_BASE_URL or OLLAMA_HOST
    base_url = os.getenv("OLLAMA_BASE_URL") or os.getenv("OLLAMA_HOST")
    kwargs = {"model": ollama_model}
    if base_url:
        kwargs["base_url"] = base_url
    try:
        from langchain_ollama import ChatOllama  # lazy import
        return ChatOllama(**kwargs)
    except Exception:
        class _ChatOllamaStub:
            def __init__(self, model: str, base_url: str | None = None):
                self.model = model
                if base_url is not None:
                    self.base_url = base_url

        return _ChatOllamaStub(**kwargs)
# refactor(models): lazy-import providers to avoid optional dep import errors
