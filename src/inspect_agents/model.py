from __future__ import annotations

"""Model resolver for Inspect-native agents.

Resolves a concrete Inspect model identifier or a role indirection string that
can be passed to `react(model=...)` or `get_model(...)`.

Rules (summary):
- Explicit `model` wins; return as-is if it contains a provider prefix ("/").
- If `role` is provided (and `model` is not), return "inspect/<role>".
- Prefer local (Ollama) by default: use `OLLAMA_MODEL_NAME` or a sensible default.
- If a remote provider is selected, fail fast when required API keys are absent.

Environment compatibility is aligned with the legacy deepagents behavior for the
two common local paths (Ollama, LM Studio) while returning Inspect-style model
strings (e.g., "ollama/<tag>", "openai-api/lm-studio/<model>").
"""

from typing import Optional
import os


LOCAL_DEFAULT_OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL_NAME", "qwen3:4b-thinking-2507-q4_K_M"
)


def resolve_model(
    provider: str | None = None,
    model: str | None = None,
    role: str | None = None,
) -> str:
    """Resolve an Inspect model identifier or a role mapping.

    Args:
        provider: Preferred provider (e.g., "ollama", "lm-studio", "openai").
        model: Explicit model (with or without provider prefix). If it contains
            a provider prefix ("/"), it is returned as-is.
        role: Model role indirection (returns "inspect/<role>" when provided
            and no explicit model is given).

    Returns:
        A model string acceptable to Inspect (e.g., "ollama/llama3.1",
        "openai/gpt-4o-mini", "openai-api/lm-studio/qwen3", or
        "inspect/<role>").

    Raises:
        RuntimeError: if a remote provider is selected without required keys.
    """

    # 1) Explicit model with provider prefix wins
    if model and "/" in model:
        return model

    # 2) Role indirection when no explicit model
    if model is None and role:
        return f"inspect/{role}"

    # 3) Env-specified full model via Inspect convention
    env_inspect_model = os.getenv("INSPECT_EVAL_MODEL")
    if model is None and env_inspect_model and "/" in env_inspect_model:
        return env_inspect_model

    # 4) Determine provider: function arg > env > default (ollama)
    provider = (provider or os.getenv("DEEPAGENTS_MODEL_PROVIDER") or "ollama").lower()

    # 5) Provider-specific resolution
    if provider in {"ollama"}:
        # Resolve model (explicit argument or env or default)
        tag = model or os.getenv("OLLAMA_MODEL_NAME") or LOCAL_DEFAULT_OLLAMA_MODEL
        return f"ollama/{tag}"

    if provider in {"lm-studio", "lmstudio"}:
        # LM Studio is OpenAI-compatible local server
        tag = model or os.getenv("LM_STUDIO_MODEL_NAME") or "local-model"
        return f"openai-api/lm-studio/{tag}"

    # Common remote providers that require API keys
    if provider in {
        "openai",
        "anthropic",
        "google",
        "groq",
        "mistral",
        "perplexity",
        "fireworks",
        "grok",
        "goodfire",
        "openrouter",
    }:
        required_env = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GOOGLE_API_KEY",
            "groq": "GROQ_API_KEY",
            "mistral": "MISTRAL_API_KEY",
            "perplexity": "PERPLEXITY_API_KEY",
            "fireworks": "FIREWORKS_API_KEY",
            "grok": "GROK_API_KEY",
            "goodfire": "GOODFIRE_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
        }[provider]
        if not os.getenv(required_env):
            raise RuntimeError(
                f"Provider '{provider}' requires {required_env} to be set."
            )
        tag = model or os.getenv(f"{provider.upper()}_MODEL")
        if not tag:
            raise RuntimeError(
                f"Model not specified for provider '{provider}'. Set the 'model' argument "
                f"or {provider.upper()}_MODEL environment variable."
            )
        return f"{provider}/{tag}"

    # OpenAI compatible generic provider: provider like "openai-api/<vendor>"
    if provider.startswith("openai-api/"):
        # provider format 'openai-api/<vendor>'
        _, vendor = provider.split("/", 1)
        env_prefix = vendor.upper().replace("-", "_")
        key_var = f"{env_prefix}_API_KEY"
        if not os.getenv(key_var):
            raise RuntimeError(
                f"Provider '{provider}' requires {key_var} to be set."
            )
        tag = model or os.getenv(f"{env_prefix}_MODEL")
        if not tag:
            raise RuntimeError(
                f"Model not specified for provider '{provider}'. Set the 'model' argument "
                f"or {env_prefix}_MODEL environment variable."
            )
        return f"openai-api/{vendor}/{tag}"

    # Fallback: if model was provided without slash (no provider), assume provider prefix
    if model:
        return f"{provider}/{model}"

    # Final fallback: prefer Ollama
    return f"ollama/{LOCAL_DEFAULT_OLLAMA_MODEL}"

