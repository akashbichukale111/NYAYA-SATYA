"""
LLMProvider abstraction.

Critical boundary: an LLM is used ONLY to draft a human-readable
suggestion (e.g. plain-language correction wording) that a human then
reviews. No LLMProvider output is ever treated as a fact about whether a
requirement is met, a defect is real, or a case is compliant — that
determination is made exclusively by the deterministic engines in
requirement_engine.py / checklist_engine.py / defect_engine.py, which
have no LLMProvider dependency at all.

DEMO mode and every existing test in this repository work with
MockProvider only (no network calls, no API key). OpenAI/Anthropic/Groq
providers are thin, optional adapters — if their SDK or API key isn't
available, callers fall back to MockProvider rather than failing.
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMSuggestion:
    text: str
    provider: str
    model: str | None = None
    is_mock: bool = False


class LLMProvider(ABC):
    name: str = "base"

    @abstractmethod
    def suggest_correction_wording(self, *, defect_description: str, context: str) -> LLMSuggestion:
        """Draft a plain-language, non-binding suggestion for how a human
        might phrase a correction. Must never assert the defect is
        resolved, never assert legal validity, and always read as a
        suggestion, not a determination."""
        raise NotImplementedError


class MockProvider(LLMProvider):
    """Deterministic, offline, zero-dependency provider. This is what
    DEMO mode and the test suite use. It performs no network access and
    requires no API key."""

    name = "mock"

    def suggest_correction_wording(self, *, defect_description: str, context: str) -> LLMSuggestion:
        text = (
            f"Suggested next step (not a legal determination): review the finding — "
            f"\"{defect_description.strip()}\" — against the source material, and if "
            f"confirmed, prepare the missing or corrected item for human approval before "
            f"any resubmission. {('Context: ' + context.strip()) if context.strip() else ''}"
        ).strip()
        return LLMSuggestion(text=text, provider=self.name, model="rule-based-template", is_mock=True)


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str | None = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model

    def suggest_correction_wording(self, *, defect_description: str, context: str) -> LLMSuggestion:
        if not self.api_key:
            return MockProvider().suggest_correction_wording(defect_description=defect_description, context=context)
        try:
            import openai  # type: ignore
            client = openai.OpenAI(api_key=self.api_key)
            prompt = _build_prompt(defect_description, context)
            resp = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
            )
            text = resp.choices[0].message.content or ""
            return LLMSuggestion(text=text.strip(), provider=self.name, model=self.model)
        except Exception:
            # Network/SDK/auth failure: never crash the request, fall back
            # to the deterministic path instead.
            return MockProvider().suggest_correction_wording(defect_description=defect_description, context=context)


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str | None = None, model: str = "claude-haiku-4-5-20251001"):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model

    def suggest_correction_wording(self, *, defect_description: str, context: str) -> LLMSuggestion:
        if not self.api_key:
            return MockProvider().suggest_correction_wording(defect_description=defect_description, context=context)
        try:
            import anthropic  # type: ignore
            client = anthropic.Anthropic(api_key=self.api_key)
            prompt = _build_prompt(defect_description, context)
            resp = client.messages.create(
                model=self.model, max_tokens=200,
                messages=[{"role": "user", "content": prompt}],
            )
            text = "".join(block.text for block in resp.content if getattr(block, "type", None) == "text")
            return LLMSuggestion(text=text.strip(), provider=self.name, model=self.model)
        except Exception:
            return MockProvider().suggest_correction_wording(defect_description=defect_description, context=context)


class GroqProvider(LLMProvider):
    name = "groq"

    def __init__(self, api_key: str | None = None, model: str = "llama-3.1-8b-instant"):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        self.model = model

    def suggest_correction_wording(self, *, defect_description: str, context: str) -> LLMSuggestion:
        if not self.api_key:
            return MockProvider().suggest_correction_wording(defect_description=defect_description, context=context)
        try:
            import groq  # type: ignore
            client = groq.Groq(api_key=self.api_key)
            prompt = _build_prompt(defect_description, context)
            resp = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
            )
            text = resp.choices[0].message.content or ""
            return LLMSuggestion(text=text.strip(), provider=self.name, model=self.model)
        except Exception:
            return MockProvider().suggest_correction_wording(defect_description=defect_description, context=context)


def _build_prompt(defect_description: str, context: str) -> str:
    return (
        "You help draft plain-language, non-binding notes for a legal filing "
        "operations tool. You are NOT a lawyer and must not state or imply a "
        "legal conclusion, compliance determination, or predicted outcome. "
        "Given this detected filing defect, suggest one short, neutral next "
        "step a human reviewer could take. Do not claim the issue is resolved.\n\n"
        f"Defect: {defect_description}\nContext: {context}"
    )


def get_provider(name: str | None = None) -> LLMProvider:
    """Factory. Defaults to MockProvider unless a name is given AND that
    provider's API key is actually configured — so calling this with no
    arguments in DEMO mode or in tests always returns a provider that
    makes no network calls."""
    name = (name or os.environ.get("LLM_PROVIDER") or "mock").lower()
    if name == "openai" and os.environ.get("OPENAI_API_KEY"):
        return OpenAIProvider()
    if name == "anthropic" and os.environ.get("ANTHROPIC_API_KEY"):
        return AnthropicProvider()
    if name == "groq" and os.environ.get("GROQ_API_KEY"):
        return GroqProvider()
    return MockProvider()
