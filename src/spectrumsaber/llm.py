"""
LLM provider abstraction for the SpectrumSaber Text2GQL feature.

Defines a common LLMProvider interface and concrete implementations for
the two supported backends:

    AnthropicProvider -- Claude models via the ``anthropic`` SDK.
    OpenAIProvider    -- GPT models via the ``openai`` SDK.

Factory:
    create_provider(name, api_key, **kwargs) -- instantiate a provider by
    name ("anthropic" or "openai"), forwarding extra kwargs (e.g. ``model``)
    to the chosen constructor.

This module is used exclusively by :mod:`spectrumsaber.text2gql` to
power natural-language-to-GraphQL translation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Base interface for LLM providers."""

    @abstractmethod
    def generate(self, system_prompt: str, user_message: str) -> str:
        """
        Generate a response given a system prompt and user message.

        Args:
            system_prompt: Instructions / context for the model.
            user_message: The user's input.

        Returns:
            The model's text response.
        """


class AnthropicProvider(LLMProvider):
    """Claude provider via the `anthropic` SDK."""

    def __init__(self, api_key: str, model: str = "claude-opus-4-6") -> None:
        try:
            import anthropic
        except ImportError as exc:
            raise ImportError(
                "Install the 'anthropic' package to use AnthropicProvider: "
                "pip install anthropic"
            ) from exc
        self._client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def generate(self, system_prompt: str, user_message: str) -> str:
        message = self._client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return message.content[0].text


class OpenAIProvider(LLMProvider):
    """GPT provider via the `openai` SDK."""

    def __init__(self, api_key: str, model: str = "gpt-4o") -> None:
        try:
            import openai
        except ImportError as exc:
            raise ImportError(
                "Install the 'openai' package to use OpenAIProvider: "
                "pip install openai"
            ) from exc
        self._client = openai.OpenAI(api_key=api_key)
        self.model = model

    def generate(self, system_prompt: str, user_message: str) -> str:
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )
        return response.choices[0].message.content


def create_provider(name: str, api_key: str, **kwargs) -> LLMProvider:
    """
    Factory function to create an LLM provider by name.

    Args:
        name: Provider name — "anthropic" or "openai".
        api_key: API key for the provider.
        **kwargs: Extra arguments forwarded to the provider constructor
                  (e.g. ``model="gpt-4o-mini"``).

    Returns:
        An LLMProvider instance.

    Raises:
        ValueError: If the provider name is unknown.
    """
    providers = {
        "anthropic": AnthropicProvider,
        "openai": OpenAIProvider,
    }
    if name not in providers:
        raise ValueError(
            f"Unknown provider '{name}'. Choose from: {list(providers)}"
        )
    return providers[name](api_key=api_key, **kwargs)
