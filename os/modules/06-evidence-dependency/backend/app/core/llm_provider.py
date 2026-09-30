"""
LLMProvider abstraction.

DEMO mode (and every automated test) uses MockProvider exclusively --
deterministic, offline, no network call, no API key. It never invents
facts: extraction only ever returns substrings that are actually present
in the input text. The paid providers below are real, structurally
correct client implementations for later use but are never exercised
by tests in this environment (no outbound network to those hosts here,
and no keys are configured in DEMO mode).
"""
import os
import re
from abc import ABC, abstractmethod
from typing import Dict, List


class LLMProvider(ABC):
    """Abstract provider boundary. Every provider implements the same
    narrow, structured contract -- nothing downstream cares which
    provider produced the result."""

    name = "abstract"

    @abstractmethod
    def extract_evidence_candidates(self, text: str, max_candidates: int = 12) -> List[Dict]:
        """Return a list of {source_text, confidence} extracted VERBATIM
        from `text`. Implementations must never return text that is not a
        substring of the input -- this is the anti-fabrication contract."""
        raise NotImplementedError

    @abstractmethod
    def detect_contradiction(self, text_a: str, text_b: str) -> Dict:
        """Return {"contradiction": bool, "explanation": str}. Heuristic
        only -- always REQUIRES_HUMAN_REVIEW downstream, never a final
        determination of truth."""
        raise NotImplementedError


class MockProvider(LLMProvider):
    """Deterministic, offline, no-key extraction used by DEMO mode and
    all automated tests. Simple sentence/line segmentation -- every
    returned candidate is a verbatim substring of the source text."""

    name = "mock"

    _SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
    _NEGATION_CUES = {"not", "no", "never", "denies", "disputes", "did not", "was not", "false"}

    def extract_evidence_candidates(self, text: str, max_candidates: int = 12) -> List[Dict]:
        if not text or not text.strip():
            return []
        raw_chunks = [c.strip() for c in self._SPLIT_RE.split(text) if c.strip()]
        candidates = []
        for chunk in raw_chunks[:max_candidates]:
            if len(chunk) < 8:
                continue
            assert chunk in text  # anti-fabrication contract, enforced at runtime
            candidates.append({"source_text": chunk, "confidence": "HEURISTIC_SEGMENTATION"})
        return candidates

    def detect_contradiction(self, text_a: str, text_b: str) -> Dict:
        a_lower = text_a.lower()
        b_lower = text_b.lower()
        a_has_neg = any(cue in a_lower for cue in self._NEGATION_CUES)
        b_has_neg = any(cue in b_lower for cue in self._NEGATION_CUES)
        # Heuristic only: one text carries a negation cue and the other doesn't,
        # while they otherwise share vocabulary -- flagged for human review, never
        # treated as a determination of which source is correct.
        shared_words = set(a_lower.split()) & set(b_lower.split())
        likely_related = len(shared_words) >= 3
        contradiction = likely_related and (a_has_neg != b_has_neg)
        return {
            "contradiction": contradiction,
            "explanation": (
                "Heuristic: related vocabulary with mismatched negation cues; "
                "requires human review."
                if contradiction else
                "Heuristic found no negation-cue mismatch between related text."
            ),
        }


class OpenAIProvider(LLMProvider):
    """Real client shape for a future OpenAI-backed extraction agent.
    Never used by DEMO mode or tests in this environment."""

    name = "openai"

    def __init__(self, api_key: str = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model
        if not self.api_key:
            raise RuntimeError(
                "OpenAIProvider requires OPENAI_API_KEY. DEMO mode does not need this -- "
                "use LLM_PROVIDER=mock instead."
            )

    def _client(self):
        import openai  # imported lazily so the dependency is optional
        return openai.OpenAI(api_key=self.api_key)

    def extract_evidence_candidates(self, text: str, max_candidates: int = 12) -> List[Dict]:
        client = self._client()
        prompt = (
            "Extract up to {n} short VERBATIM excerpts from the following document text "
            "that could serve as evidence items. Return each excerpt EXACTLY as it appears "
            "in the source; do not paraphrase or invent content.\n\n{text}"
        ).format(n=max_candidates, text=text[:8000])
        resp = client.chat.completions.create(
            model=self.model, messages=[{"role": "user", "content": prompt}],
        )
        content = resp.choices[0].message.content or ""
        lines = [l.strip("- ").strip() for l in content.splitlines() if l.strip()]
        # Anti-fabrication guard: only keep lines that are verbatim substrings of the source.
        return [{"source_text": l, "confidence": "LLM_EXTRACTED"} for l in lines if l in text]

    def detect_contradiction(self, text_a: str, text_b: str) -> Dict:
        client = self._client()
        prompt = (
            f"Do these two statements appear to contradict each other? Answer YES or NO on "
            f"the first line, then a one-sentence reason.\nA: {text_a}\nB: {text_b}"
        )
        resp = client.chat.completions.create(
            model=self.model, messages=[{"role": "user", "content": prompt}],
        )
        content = (resp.choices[0].message.content or "").strip()
        first_line = content.splitlines()[0].upper() if content else ""
        return {"contradiction": first_line.startswith("YES"), "explanation": content}


class AnthropicProvider(LLMProvider):
    """Real client shape for a future Claude-backed extraction agent.
    Never used by DEMO mode or tests in this environment."""

    name = "anthropic"

    def __init__(self, api_key: str = None, model: str = "claude-sonnet-4-6"):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        if not self.api_key:
            raise RuntimeError(
                "AnthropicProvider requires ANTHROPIC_API_KEY. DEMO mode does not need this -- "
                "use LLM_PROVIDER=mock instead."
            )

    def _client(self):
        import anthropic  # imported lazily so the dependency is optional
        return anthropic.Anthropic(api_key=self.api_key)

    def extract_evidence_candidates(self, text: str, max_candidates: int = 12) -> List[Dict]:
        client = self._client()
        prompt = (
            "Extract up to {n} short VERBATIM excerpts from the following document text "
            "that could serve as evidence items. Return each excerpt EXACTLY as it appears "
            "in the source, one per line; do not paraphrase or invent content.\n\n{text}"
        ).format(n=max_candidates, text=text[:8000])
        resp = client.messages.create(
            model=self.model, max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )
        content = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
        lines = [l.strip("- ").strip() for l in content.splitlines() if l.strip()]
        return [{"source_text": l, "confidence": "LLM_EXTRACTED"} for l in lines if l in text]

    def detect_contradiction(self, text_a: str, text_b: str) -> Dict:
        client = self._client()
        prompt = (
            f"Do these two statements appear to contradict each other? Answer YES or NO on "
            f"the first line, then a one-sentence reason.\nA: {text_a}\nB: {text_b}"
        )
        resp = client.messages.create(
            model=self.model, max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        content = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text").strip()
        first_line = content.splitlines()[0].upper() if content else ""
        return {"contradiction": first_line.startswith("YES"), "explanation": content}


class GroqProvider(LLMProvider):
    """Real client shape for a future Groq-backed extraction agent.
    Never used by DEMO mode or tests in this environment."""

    name = "groq"

    def __init__(self, api_key: str = None, model: str = "llama-3.1-70b-versatile"):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        self.model = model
        if not self.api_key:
            raise RuntimeError(
                "GroqProvider requires GROQ_API_KEY. DEMO mode does not need this -- "
                "use LLM_PROVIDER=mock instead."
            )

    def _client(self):
        import groq  # imported lazily so the dependency is optional
        return groq.Groq(api_key=self.api_key)

    def extract_evidence_candidates(self, text: str, max_candidates: int = 12) -> List[Dict]:
        client = self._client()
        prompt = (
            "Extract up to {n} short VERBATIM excerpts from the following document text "
            "that could serve as evidence items. Return each excerpt EXACTLY as it appears "
            "in the source, one per line; do not paraphrase or invent content.\n\n{text}"
        ).format(n=max_candidates, text=text[:8000])
        resp = client.chat.completions.create(
            model=self.model, messages=[{"role": "user", "content": prompt}],
        )
        content = resp.choices[0].message.content or ""
        lines = [l.strip("- ").strip() for l in content.splitlines() if l.strip()]
        return [{"source_text": l, "confidence": "LLM_EXTRACTED"} for l in lines if l in text]

    def detect_contradiction(self, text_a: str, text_b: str) -> Dict:
        client = self._client()
        prompt = (
            f"Do these two statements appear to contradict each other? Answer YES or NO on "
            f"the first line, then a one-sentence reason.\nA: {text_a}\nB: {text_b}"
        )
        resp = client.chat.completions.create(
            model=self.model, messages=[{"role": "user", "content": prompt}],
        )
        content = (resp.choices[0].message.content or "").strip()
        first_line = content.splitlines()[0].upper() if content else ""
        return {"contradiction": first_line.startswith("YES"), "explanation": content}


_PROVIDERS = {
    "mock": MockProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "groq": GroqProvider,
}


def get_llm_provider(name: str = None) -> LLMProvider:
    """Factory. Defaults to MockProvider (LLM_PROVIDER env, default 'mock')
    so DEMO mode and every test path work with zero API keys."""
    key = (name or os.environ.get("LLM_PROVIDER", "mock")).lower()
    cls = _PROVIDERS.get(key)
    if not cls:
        raise ValueError(f"Unknown LLM_PROVIDER '{key}'. Valid: {list(_PROVIDERS)}")
    return cls()
