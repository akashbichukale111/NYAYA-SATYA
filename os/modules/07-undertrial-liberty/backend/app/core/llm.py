"""
LLM Provider abstraction.

DEMO mode (default) uses MockProvider and requires no external API key.
Real providers are implemented but only activated when LLM_PROVIDER is set
and the corresponding API key is present. No provider is ever allowed to
take autonomous action -- see agents/ for how outputs are constrained to
structured, human-reviewable suggestions only.
"""
import json
import re
from abc import ABC, abstractmethod
from typing import Optional

from app.core.config import settings


class LLMProvider(ABC):
    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        ...


class MockProvider(LLMProvider):
    """
    Deterministic, rule-based 'extraction' used for DEMO mode and tests.
    It does NOT call any network API. It looks for known keyword patterns
    in the input text and returns structured JSON matching what a real
    extraction agent would produce. This keeps DEMO mode fully offline,
    deterministic, and reproducible.
    """

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        # The mock provider's "intelligence" lives in app/agents/extraction.py,
        # which uses pattern matching directly rather than routing through
        # this method. This method exists to satisfy the LLMProvider
        # interface uniformly and is used only for illustrative echo-back
        # in the Evaluation Lab's provider-connectivity check.
        return json.dumps({
            "provider": "mock",
            "note": "MockProvider does not perform network calls. "
                    "Deterministic extraction is handled by rule-based agents.",
        })


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY not configured.")
        import httpx
        resp = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not configured.")
        import httpx
        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 1000,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return "".join(block.get("text", "") for block in data.get("content", []))


class GroqProvider(LLMProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        if not self.api_key:
            raise RuntimeError("GROQ_API_KEY not configured.")
        import httpx
        resp = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": "llama-3.1-70b-versatile",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


def get_llm_provider() -> LLMProvider:
    provider = settings.LLM_PROVIDER.lower()
    if provider == "openai" and settings.OPENAI_API_KEY:
        return OpenAIProvider(settings.OPENAI_API_KEY)
    if provider == "anthropic" and settings.ANTHROPIC_API_KEY:
        return AnthropicProvider(settings.ANTHROPIC_API_KEY)
    if provider == "groq" and settings.GROQ_API_KEY:
        return GroqProvider(settings.GROQ_API_KEY)
    return MockProvider()
