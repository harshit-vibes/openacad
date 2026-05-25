"""Single source for the LLM model spec consumed by PydanticAI agents.

For OpenAI / Anthropic / DeepSeek we return a string identifier; PydanticAI
infers the provider. For OpenRouter we return a fully configured
`OpenAIChatModel` instance because it needs a custom base_url + api_key.
"""

from typing import Any

from openacad.runtime.settings import settings


def model_for(role: str) -> Any:
    """Return what PydanticAI Agent(model=...) wants. role: 'extraction' | 'synthesis'."""
    if role not in {"extraction", "synthesis"}:
        raise ValueError(f"unknown role: {role}")
    provider = settings.llm_provider

    if provider == "openrouter":
        # Lazy import — pulled into module scope only when OpenRouter is the active provider.
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider

        name = settings.extraction_model if role == "extraction" else settings.synthesis_model
        oai_provider = OpenAIProvider(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
        )
        return OpenAIChatModel(name, provider=oai_provider)

    # Provider:model strings recognized natively by PydanticAI.
    name = settings.extraction_model if role == "extraction" else settings.synthesis_model
    return f"{provider}:{name}"


def model_string(role: str) -> Any:
    """Back-compat alias used by extraction_agent / synthesis_agent / baselines."""
    return model_for(role)


# ── token-budget guardrails ─────────────────────────────────────────────
#
# Every Agent(...) construction in this codebase passes `model_settings=...` so
# OpenRouter only reserves credits for what we'll actually use. Without this,
# models with huge default output windows (Grok 4.3 = 65k) force OpenRouter to
# hold the full window in escrow and throw HTTP 402 even when there's plenty of
# real credit available.
#
# Per-role caps: synthesis answers are 200-1500 tokens in practice; extraction
# returns up to ~20 ProposedAtoms × ~150 tokens each.

DEFAULT_MAX_TOKENS = 4000

EXTRACTION_SETTINGS: dict[str, Any] = {"max_tokens": DEFAULT_MAX_TOKENS}
SYNTHESIS_SETTINGS: dict[str, Any] = {"max_tokens": 2500}


def settings_for(role: str) -> dict[str, Any]:
    """model_settings dict to pass to Agent(..., model_settings=...)."""
    if role == "extraction":
        return EXTRACTION_SETTINGS
    if role == "synthesis":
        return SYNTHESIS_SETTINGS
    raise ValueError(f"unknown role: {role}")


def have_api_key() -> bool:
    if settings.llm_provider == "anthropic":
        return bool(settings.anthropic_api_key)
    if settings.llm_provider == "openai":
        return bool(settings.openai_api_key)
    if settings.llm_provider == "openrouter":
        return bool(settings.openrouter_api_key)
    if settings.llm_provider == "deepseek":
        return bool(settings.deepseek_api_key)
    return False
