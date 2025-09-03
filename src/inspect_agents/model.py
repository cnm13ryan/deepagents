from __future__ import annotations

# ruff: noqa: E402
"""Model resolver for Inspect-native agents.

Resolves a concrete Inspect model identifier or a role indirection string that
can be passed to `react(model=...)` or `get_model(...)`.

Rules (summary):
- Explicit `model` wins; return as-is if it contains a provider prefix ("/").
- If `role` is provided (and `model` is not), consult role → model env mapping
  and otherwise return "inspect/<role>".
- Prefer local (Ollama) by default: use `OLLAMA_MODEL_NAME` or a sensible default.
- If a remote provider is selected, fail fast when required API keys are absent.

Environment compatibility is aligned with the legacy deepagents behavior for the
two common local paths (Ollama, LM Studio) while returning Inspect-style model
strings (e.g., "ollama/<tag>", "openai-api/lm-studio/<model>").
"""

import logging
import os

LOCAL_DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL_NAME", "qwen3:4b-thinking-2507-q4_K_M")

# Default roles known to the repository. These do not enforce a concrete model
# by default; in absence of env mapping they resolve to the Inspect role indirection
# string ("inspect/<role>") so that environments with Inspect-native role routing
# continue to work. Repositories may choose to add stricter defaults later.
DEFAULT_ROLES: tuple[str, ...] = (
    "researcher",
    "coder",
    "editor",
    "grader",
)


def _role_env_key(role: str) -> str:
    return f"INSPECT_ROLE_{role.upper().replace('-', '_')}"  # prefix; add _MODEL etc.


def _resolve_role_mapping(role: str) -> tuple[str | None, str | None]:
    """Resolve provider/model from role-specific env, if configured.

    Env precedence (if present):
    - INSPECT_ROLE_<ROLE>_MODEL: if value contains '/', interpret as
      '<provider-path>/<model-tag>' (e.g., 'openai-api/lm-studio/qwen3').
      Otherwise treat as a bare model tag to be combined with provider
      INSPECT_ROLE_<ROLE>_PROVIDER or default provider resolution.

    Returns:
        (provider, model) or (None, None) if no mapping is configured.
    """

    base = _role_env_key(role)
    raw = os.getenv(f"{base}_MODEL")
    if not raw:
        _log_role_mapping_debug(role, base, None, None, None, None, "no_model_env")
        return (None, None)

    raw = raw.strip()
    if "/" in raw:
        # Split '<provider-path>/<tag>' while allowing provider paths that contain '/'
        *provider_parts, tag = raw.split("/")
        provider = "/".join(provider_parts)
        _log_role_mapping_debug(role, base, raw, provider, tag, None, "provider_in_model")
        return (provider, tag)

    # Bare model tag; find provider override or fall back to default chain
    provider_env = os.getenv(f"{base}_PROVIDER")
    provider = None
    if provider_env:
        provider = provider_env.strip().lower()
    _log_role_mapping_debug(role, base, raw, provider, raw, provider_env, "bare_model_tag")
    return (provider, raw)


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

    # Capture initial state for debug logging
    provider_arg = provider
    model_arg = model
    role_env_model = None
    role_env_provider = None
    path = None

    # 1) Explicit model with provider prefix wins (caller-originated only)
    if model and "/" in model:
        path = "explicit_model_with_provider"
        final_result = model
        _log_model_debug(
            role=role,
            provider_arg=provider_arg,
            model_arg=model_arg,
            role_env_model=role_env_model,
            role_env_provider=role_env_provider,
            env_INSPECT_EVAL_MODEL=os.getenv("INSPECT_EVAL_MODEL"),
            final=final_result,
            path=path,
        )
        return final_result

    # 2) Role-mapped resolution when role is provided and no explicit model
    if model is None and role:
        # Env-mapped provider/model for role, if any
        r_provider, r_model = _resolve_role_mapping(role)
        role_env_provider = r_provider
        role_env_model = r_model
        if r_provider or r_model:
            # r_provider may be None (falls through to default provider chain)
            provider = r_provider or provider
            model = r_model
            path = "role_env_mapping"
        else:
            # No mapping configured; return Inspect role indirection
            path = "role_inspect_indirection"
            final_result = f"inspect/{role}"
            _log_model_debug(
                role=role,
                provider_arg=provider_arg,
                model_arg=model_arg,
                role_env_model=role_env_model,
                role_env_provider=role_env_provider,
                env_INSPECT_EVAL_MODEL=os.getenv("INSPECT_EVAL_MODEL"),
                final=final_result,
                path=path,
            )
            return final_result

    # 3) Env-specified full model via Inspect convention
    env_inspect_model = os.getenv("INSPECT_EVAL_MODEL")
    if (
        model is None
        and env_inspect_model
        and "/" in env_inspect_model
        and env_inspect_model.strip().lower() != "none/none"
    ):
        path = "env_INSPECT_EVAL_MODEL"
        final_result = env_inspect_model
        _log_model_debug(
            role=role,
            provider_arg=provider_arg,
            model_arg=model_arg,
            role_env_model=role_env_model,
            role_env_provider=role_env_provider,
            env_INSPECT_EVAL_MODEL=env_inspect_model,
            final=final_result,
            path=path,
        )
        return final_result

    # 4) Determine provider: function arg > env > default (ollama)
    provider = (provider or os.getenv("DEEPAGENTS_MODEL_PROVIDER") or "ollama").lower()

    # 5) Provider-specific resolution
    if provider in {"ollama"}:
        # Resolve model (explicit argument or env or default)
        tag = model or os.getenv("OLLAMA_MODEL_NAME") or LOCAL_DEFAULT_OLLAMA_MODEL
        path = "provider_ollama"
        final_result = f"ollama/{tag}"
        _log_model_debug(
            role=role,
            provider_arg=provider_arg,
            model_arg=model_arg,
            role_env_model=role_env_model,
            role_env_provider=role_env_provider,
            env_INSPECT_EVAL_MODEL=env_inspect_model,
            final=final_result,
            path=path,
        )
        return final_result

    if provider in {"lm-studio", "lmstudio"}:
        # LM Studio is OpenAI-compatible local server
        tag = model or os.getenv("LM_STUDIO_MODEL_NAME") or "local-model"
        path = "provider_lm_studio"
        final_result = f"openai-api/lm-studio/{tag}"
        _log_model_debug(
            role=role,
            provider_arg=provider_arg,
            model_arg=model_arg,
            role_env_model=role_env_model,
            role_env_provider=role_env_provider,
            env_INSPECT_EVAL_MODEL=env_inspect_model,
            final=final_result,
            path=path,
        )
        return final_result

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
            raise RuntimeError(f"Provider '{provider}' requires {required_env} to be set.")
        tag = model or os.getenv(f"{provider.upper()}_MODEL")
        if not tag:
            raise RuntimeError(
                f"Model not specified for provider '{provider}'. Set the 'model' argument "
                f"or {provider.upper()}_MODEL environment variable."
            )
        path = f"provider_{provider}"
        final_result = f"{provider}/{tag}"
        _log_model_debug(
            role=role,
            provider_arg=provider_arg,
            model_arg=model_arg,
            role_env_model=role_env_model,
            role_env_provider=role_env_provider,
            env_INSPECT_EVAL_MODEL=env_inspect_model,
            final=final_result,
            path=path,
        )
        return final_result

    # OpenAI compatible generic provider: provider like "openai-api/<vendor>"
    if provider.startswith("openai-api/"):
        # provider format 'openai-api/<vendor>'
        _, vendor = provider.split("/", 1)
        env_prefix = vendor.upper().replace("-", "_")
        key_var = f"{env_prefix}_API_KEY"
        if not os.getenv(key_var):
            raise RuntimeError(f"Provider '{provider}' requires {key_var} to be set.")
        tag = model or os.getenv(f"{env_prefix}_MODEL")
        if not tag:
            raise RuntimeError(
                f"Model not specified for provider '{provider}'. Set the 'model' argument "
                f"or {env_prefix}_MODEL environment variable."
            )
        path = f"provider_openai_api_{vendor}"
        final_result = f"openai-api/{vendor}/{tag}"
        _log_model_debug(
            role=role,
            provider_arg=provider_arg,
            model_arg=model_arg,
            role_env_model=role_env_model,
            role_env_provider=role_env_provider,
            env_INSPECT_EVAL_MODEL=env_inspect_model,
            final=final_result,
            path=path,
        )
        return final_result

    # Fallback: if model was provided without slash (no provider), assume provider prefix
    if model:
        path = "fallback_model_with_provider"
        final_result = f"{provider}/{model}"
        _log_model_debug(
            role=role,
            provider_arg=provider_arg,
            model_arg=model_arg,
            role_env_model=role_env_model,
            role_env_provider=role_env_provider,
            env_INSPECT_EVAL_MODEL=env_inspect_model,
            final=final_result,
            path=path,
        )
        return final_result

    # Final fallback: prefer Ollama
    path = "final_fallback_ollama"
    final_result = f"ollama/{LOCAL_DEFAULT_OLLAMA_MODEL}"
    _log_model_debug(
        role=role,
        provider_arg=provider_arg,
        model_arg=model_arg,
        role_env_model=role_env_model,
        role_env_provider=role_env_provider,
        env_INSPECT_EVAL_MODEL=env_inspect_model,
        final=final_result,
        path=path,
    )
    return final_result


def _log_model_debug(
    role: str | None,
    provider_arg: str | None,
    model_arg: str | None,
    role_env_model: str | None,
    role_env_provider: str | None,
    env_INSPECT_EVAL_MODEL: str | None,
    final: str,
    path: str,
) -> None:
    """Log model resolution debug information when INSPECT_MODEL_DEBUG is set."""
    if not os.getenv("INSPECT_MODEL_DEBUG"):
        return

    logger = logging.getLogger(__name__)
    logger.info(
        "Model resolution: role=%s provider_arg=%s model_arg=%s "
        "role_env_model=%s role_env_provider=%s env_INSPECT_EVAL_MODEL=%s "
        "final=%s path=%s",
        role,
        provider_arg,
        model_arg,
        role_env_model,
        role_env_provider,
        env_INSPECT_EVAL_MODEL,
        final,
        path,
    )


def _log_role_mapping_debug(
    role: str,
    base: str,
    raw: str | None,
    provider: str | None,
    model: str | None,
    provider_env: str | None,
    path: str,
) -> None:
    """Log role mapping resolution debug information when INSPECT_MODEL_DEBUG is set."""
    if not os.getenv("INSPECT_MODEL_DEBUG"):
        return

    logger = logging.getLogger(__name__)
    logger.info(
        "Role mapping resolution: role=%s base=%s raw=%s provider=%s model=%s provider_env=%s path=%s",
        role,
        base,
        raw,
        provider,
        model,
        provider_env,
        path,
    )
