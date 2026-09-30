"""
LLMProvider abstraction (sec 66).

Env vars: LLM_API_KEY, LLM_MODEL, LLM_BASE_URL.
If LLM_API_KEY is unset, falls back to a deterministic MOCK/DEMO provider
so the whole system runs offline with no external calls. The frontend
never receives an API key — this module only runs server-side.
"""
import os
import time
from dataclasses import dataclass


@dataclass
class LLMResult:
    text: str
    provider: str
    latency_ms: int


class LLMProvider:
    def complete(self, system: str, prompt: str) -> LLMResult:
        raise NotImplementedError


class MockProvider(LLMProvider):
    """Deterministic, template-based responses — no network call.
    Used automatically when no LLM_API_KEY is configured, and in all
    automated tests, so demo behaviour is reproducible."""

    def complete(self, system: str, prompt: str) -> LLMResult:
        start = time.time()
        # Deterministic templated "reasoning" — clearly labeled as such.
        text = (
            "[MOCK PROVIDER — DEMO MODE, no external LLM call made]\n"
            "Based on the structured case state provided, no additional "
            "unstructured inference was generated; refer to the rule-based "
            "engine output for this step."
        )
        latency = int((time.time() - start) * 1000)
        return LLMResult(text=text, provider="MOCK", latency_ms=latency)


class AnthropicProvider(LLMProvider):
    """Real provider — only constructed if LLM_API_KEY is present."""

    def __init__(self):
        import anthropic  # imported lazily; not a hard dependency in demo mode
        self.client = anthropic.Anthropic(
            api_key=os.environ["LLM_API_KEY"],
            base_url=os.environ.get("LLM_BASE_URL") or None,
        )
        self.model = os.environ.get("LLM_MODEL", "claude-sonnet-4-6")

    def complete(self, system: str, prompt: str) -> LLMResult:
        start = time.time()
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=800,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        latency = int((time.time() - start) * 1000)
        return LLMResult(text=text, provider=self.model, latency_ms=latency)


def get_provider() -> LLMProvider:
    if os.environ.get("LLM_API_KEY"):
        try:
            return AnthropicProvider()
        except Exception:
            return MockProvider()
    return MockProvider()
