"""
LLM Provider abstraction.

CRITICAL: LLMs never compute graph state. They may only be asked to phrase a
plain-language EXPLANATION of an already-computed, deterministic simulation
result. DEMO mode (MockProvider) requires no API keys and is the default.
"""

from __future__ import annotations
import os
import json
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    def explain(self, prompt: str) -> str:
        ...


class MockProvider(LLMProvider):
    """Deterministic, offline explanation generator. Used in DEMO mode."""

    def explain(self, prompt: str) -> str:
        return (
            "[DEMO MODE — deterministic explanation, no external model called]\n"
            "This simulation result was computed entirely by the deterministic "
            "graph/rule engine. The explanation below only restates that result "
            "in plain language and adds no new facts:\n\n" + _summarize(prompt)
        )


def _summarize(prompt: str) -> str:
    # Best-effort plain-language restatement without inventing facts.
    return prompt[:800] + ("..." if len(prompt) > 800 else "")


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str | None = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model

    def explain(self, prompt: str) -> str:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY not configured")
        import urllib.request

        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps({
                "model": self.model,
                "messages": [
                    {"role": "system", "content": SYSTEM_GUARDRAIL},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 500,
            }).encode(),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"]


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str | None = None, model: str = "claude-sonnet-4-6"):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model

    def explain(self, prompt: str) -> str:
        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not configured")
        import urllib.request

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps({
                "model": self.model,
                "max_tokens": 500,
                "system": SYSTEM_GUARDRAIL,
                "messages": [{"role": "user", "content": prompt}],
            }).encode(),
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        return "".join(block.get("text", "") for block in data.get("content", []))


class GroqProvider(LLMProvider):
    def __init__(self, api_key: str | None = None, model: str = "llama-3.3-70b-versatile"):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        self.model = model

    def explain(self, prompt: str) -> str:
        if not self.api_key:
            raise RuntimeError("GROQ_API_KEY not configured")
        import urllib.request

        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=json.dumps({
                "model": self.model,
                "messages": [
                    {"role": "system", "content": SYSTEM_GUARDRAIL},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 500,
            }).encode(),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"]


SYSTEM_GUARDRAIL = (
    "You explain already-computed, deterministic case-graph simulation results "
    "in plain language. You must not predict judicial or legal outcomes, "
    "guilt, innocence, conviction, acquittal, or bail results. You must not "
    "invent facts, dates, or legal rules not present in the input. Restate "
    "structural graph findings (gaps, conflicts, blocks, review items) only."
)


def get_provider(name: str = "mock") -> LLMProvider:
    name = (name or "mock").lower()
    if name == "mock":
        return MockProvider()
    if name == "openai":
        return OpenAIProvider()
    if name == "anthropic":
        return AnthropicProvider()
    if name == "groq":
        return GroqProvider()
    raise ValueError(f"Unknown LLM provider: {name}")
