"""
Description: Concrete LLM provider implementations for Anthropic, OpenAI,
             Google Gemini, and Ollama (local). Each wraps the provider's
             SDK using credentials from config.ini.
Source Data: config.ini [llm] section for provider/model selection.
             Provider-specific sections for API keys.
Outputs: Text responses via the BaseLLM.complete() interface.
"""

from agent.llm.base import BaseLLM
from agent.credentials import get_raw


# ---------------------------------------------------------------------------
# Anthropic (Claude)
# ---------------------------------------------------------------------------

class AnthropicLLM(BaseLLM):
    """
    Anthropic Claude provider.

    config.ini:
        [llm]
        provider = anthropic
        model    = claude-sonnet-4-5   # or claude-opus-4, claude-haiku-3-5, etc.

        [anthropic]
        api_key  = sk-ant-...
    """

    def __init__(self, model: str):
        try:
            import anthropic as _anthropic
        except ImportError:
            raise ImportError("Install the Anthropic SDK: pip install anthropic")
        self._client = _anthropic.Anthropic(api_key=get_raw("anthropic", "api_key"))
        self._model  = model

    @property
    def provider(self) -> str:
        return "anthropic"

    @property
    def model(self) -> str:
        return self._model

    def complete(self, prompt: str, system: str | None = None, max_tokens: int = 1024) -> str:
        kwargs = {"model": self._model, "max_tokens": max_tokens,
                  "messages": [{"role": "user", "content": prompt}]}
        if system:
            kwargs["system"] = system
        msg = self._client.messages.create(**kwargs)
        return msg.content[0].text


# ---------------------------------------------------------------------------
# OpenAI (GPT)
# ---------------------------------------------------------------------------

class OpenAILLM(BaseLLM):
    """
    OpenAI GPT provider.

    config.ini:
        [llm]
        provider = openai
        model    = gpt-4o-mini   # or gpt-4o, gpt-4-turbo, etc.

        [openai]
        api_key  = sk-...
    """

    def __init__(self, model: str):
        try:
            import openai as _openai
        except ImportError:
            raise ImportError("Install the OpenAI SDK: pip install openai")
        self._client = _openai.OpenAI(api_key=get_raw("openai", "api_key"))
        self._model  = model

    @property
    def provider(self) -> str:
        return "openai"

    @property
    def model(self) -> str:
        return self._model

    def complete(self, prompt: str, system: str | None = None, max_tokens: int = 1024) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = self._client.chat.completions.create(
            model=self._model, messages=messages, max_tokens=max_tokens
        )
        return resp.choices[0].message.content


# ---------------------------------------------------------------------------
# Google Gemini
# ---------------------------------------------------------------------------

class GeminiLLM(BaseLLM):
    """
    Google Gemini provider.

    config.ini:
        [llm]
        provider = google
        model    = gemini-2.0-flash   # or gemini-1.5-pro, etc.

        [google]
        api_key  = AIza...
    """

    def __init__(self, model: str):
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError("Install the Google AI SDK: pip install google-generativeai")
        genai.configure(api_key=get_raw("google", "api_key"))
        self._client = genai.GenerativeModel(model)
        self._model  = model

    @property
    def provider(self) -> str:
        return "google"

    @property
    def model(self) -> str:
        return self._model

    def complete(self, prompt: str, system: str | None = None, max_tokens: int = 1024) -> str:
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        resp = self._client.generate_content(
            full_prompt,
            generation_config={"max_output_tokens": max_tokens},
        )
        return resp.text


# ---------------------------------------------------------------------------
# Ollama (local)
# ---------------------------------------------------------------------------

class OllamaLLM(BaseLLM):
    """
    Ollama local provider — runs models locally, no API key required.

    config.ini:
        [llm]
        provider = ollama
        model    = llama3.2   # or mistral, gemma3, phi4, etc.

        [ollama]
        base_url = http://localhost:11434   # default Ollama endpoint
    """

    def __init__(self, model: str):
        try:
            import requests as _requests
            self._requests = _requests
        except ImportError:
            raise ImportError("Install requests: pip install requests")

        try:
            base_url = get_raw("ollama", "base_url")
        except (KeyError, Exception):
            base_url = "http://localhost:11434"

        self._base_url = base_url.rstrip("/")
        self._model    = model

    @property
    def provider(self) -> str:
        return "ollama"

    @property
    def model(self) -> str:
        return self._model

    def complete(self, prompt: str, system: str | None = None, max_tokens: int = 1024) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        resp = self._requests.post(
            f"{self._base_url}/api/chat",
            json={"model": self._model, "messages": messages, "stream": False,
                  "options": {"num_predict": max_tokens}},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]
