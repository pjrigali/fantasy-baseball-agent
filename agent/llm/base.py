"""
Description: Abstract base class for LLM providers. All providers expose the
             same interface so the rest of the agent is provider-agnostic.
Source Data: N/A — interface definition only.
Outputs: N/A — interface definition only.
"""

from abc import ABC, abstractmethod


class BaseLLM(ABC):
    """
    Provider-agnostic LLM interface.

    Usage:
        from agent.llm import get_llm
        llm = get_llm()
        response = llm.complete("Summarize this roster analysis: ...")
    """

    @property
    @abstractmethod
    def provider(self) -> str:
        """Human-readable provider name, e.g. 'anthropic', 'openai'."""

    @property
    @abstractmethod
    def model(self) -> str:
        """Model identifier as configured."""

    @abstractmethod
    def complete(self, prompt: str, system: str | None = None, max_tokens: int = 1024) -> str:
        """
        Send a prompt and return the text response.

        Args:
            prompt:     The user message / prompt text.
            system:     Optional system prompt to set context/persona.
            max_tokens: Maximum tokens in the response.

        Returns:
            Response text as a plain string.
        """

    def summarize(self, content: str, context: str = "fantasy baseball analysis") -> str:
        """
        Convenience method: summarize a block of content with a standard system prompt.
        """
        system = (
            f"You are a concise fantasy baseball analyst. "
            f"Summarize the following {context} in plain English. "
            f"Be direct, highlight the most actionable insights, and keep it under 200 words."
        )
        return self.complete(prompt=content, system=system, max_tokens=512)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(provider={self.provider}, model={self.model})"
