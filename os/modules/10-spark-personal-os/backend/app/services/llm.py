"""
LLM provider abstraction.

Core workspace functionality (attention, tasks, deadlines, reviews, approvals,
digest) never depends on an LLM being configured. Where AI assistance is used
(e.g. natural-language search phrasing help), it goes through this interface
so the underlying provider can be swapped without touching call sites, and so
DEMO mode works fully offline with MockProvider.
"""
from abc import ABC, abstractmethod

from app.core.config import settings


class LLMProvider(ABC):
    @abstractmethod
    def complete(self, prompt: str, *, system: str | None = None) -> str:
        ...


class MockProvider(LLMProvider):
    """Deterministic, offline provider used in DEMO mode. No network calls."""

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        return (
            "[DEMO MODE — MockProvider] No live LLM is configured. "
            "This is a placeholder response so the workspace remains fully "
            "functional without an API key. Prompt received: "
            f"{prompt[:200]}"
        )


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        import httpx

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": "gpt-4o-mini", "messages": messages},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        import httpx

        payload = {
            "model": "claude-sonnet-4-6",
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            payload["system"] = system
        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        blocks = resp.json().get("content", [])
        return "".join(b.get("text", "") for b in blocks if b.get("type") == "text")


class GroqProvider(LLMProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        import httpx

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": "llama-3.1-70b-versatile", "messages": messages},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


def get_llm_provider() -> LLMProvider:
    if settings.DEMO_MODE or settings.LLM_PROVIDER == "mock":
        return MockProvider()
    if settings.LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY:
        return OpenAIProvider(settings.OPENAI_API_KEY)
    if settings.LLM_PROVIDER == "anthropic" and settings.ANTHROPIC_API_KEY:
        return AnthropicProvider(settings.ANTHROPIC_API_KEY)
    if settings.LLM_PROVIDER == "groq" and settings.GROQ_API_KEY:
        return GroqProvider(settings.GROQ_API_KEY)
    return MockProvider()
