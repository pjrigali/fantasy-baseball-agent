"""
Description: Provider-agnostic LLM factory. Reads provider and model from
             config.ini [llm] section and returns the appropriate client.
             Supports Anthropic, OpenAI, Google Gemini, and Ollama (local).
Source Data: config.ini [llm] section.
Outputs: BaseLLM instance ready to call .complete() or .summarize().

Usage:
    from agent.llm import get_llm
    llm = get_llm()
    response = llm.complete("What should I do with my roster this week?")
    summary  = llm.summarize(analysis_text, context="matchup preview")

config.ini example:
    [llm]
    provider = anthropic          # anthropic | openai | google | ollama
    model    = claude-sonnet-4-5  # provider-specific model name
"""

from agent.llm.base import BaseLLM

_DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-5",
    "openai":    "gpt-4o-mini",
    "google":    "gemini-2.0-flash",
    "ollama":    "llama3.2",
}


def get_llm(provider: str | None = None, model: str | None = None) -> BaseLLM:
    """
    Return a configured LLM client.

    Args:
        provider: Override the provider from config.ini.
                  One of: 'anthropic', 'openai', 'google', 'ollama'.
        model:    Override the model from config.ini.

    Returns:
        A BaseLLM instance for the configured provider.

    Raises:
        ValueError:       If the provider is unknown or not configured.
        FileNotFoundError: If config.ini is missing.
        ImportError:      If the required SDK is not installed.
    """
    from agent.credentials import load_config

    cfg = load_config()

    if not provider:
        if cfg.has_section("llm") and cfg.has_option("llm", "provider"):
            provider = cfg.get("llm", "provider").strip().lower()
        else:
            raise ValueError(
                "No LLM provider configured. Add a [llm] section to config.ini:\n\n"
                "  [llm]\n"
                "  provider = anthropic   # or openai, google, ollama\n"
                "  model    = claude-sonnet-4-5\n"
            )

    if not model:
        if cfg.has_section("llm") and cfg.has_option("llm", "model"):
            model = cfg.get("llm", "model").strip()
        else:
            model = _DEFAULT_MODELS.get(provider)
            if not model:
                raise ValueError(f"Unknown provider '{provider}'. "
                                 f"Supported: {list(_DEFAULT_MODELS.keys())}")

    from agent.llm.providers import AnthropicLLM, OpenAILLM, GeminiLLM, OllamaLLM

    _registry = {
        "anthropic": AnthropicLLM,
        "openai":    OpenAILLM,
        "google":    GeminiLLM,
        "ollama":    OllamaLLM,
    }

    cls = _registry.get(provider)
    if not cls:
        raise ValueError(f"Unknown provider '{provider}'. "
                         f"Supported: {list(_registry.keys())}")

    return cls(model=model)


def is_configured() -> bool:
    """Return True if an LLM is configured in config.ini."""
    try:
        from agent.credentials import load_config
        cfg = load_config()
        return cfg.has_section("llm") and cfg.has_option("llm", "provider")
    except Exception:
        return False
