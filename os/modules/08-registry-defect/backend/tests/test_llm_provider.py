from app.services.llm_provider import MockProvider, OpenAIProvider, AnthropicProvider, GroqProvider, get_provider


def test_mock_provider_never_claims_resolution():
    provider = MockProvider()
    suggestion = provider.suggest_correction_wording(
        defect_description="Annexure B is missing", context="Petition references it directly."
    )
    assert suggestion.is_mock is True
    assert "resolved" not in suggestion.text.lower()
    assert "compliant" not in suggestion.text.lower()


def test_get_provider_defaults_to_mock_with_no_config(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    provider = get_provider()
    assert provider.name == "mock"


def test_get_provider_falls_back_to_mock_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    provider = get_provider("openai")
    assert provider.name == "mock"


def test_openai_provider_falls_back_without_key():
    provider = OpenAIProvider(api_key=None)
    suggestion = provider.suggest_correction_wording(defect_description="x", context="")
    assert suggestion.is_mock is True


def test_anthropic_provider_falls_back_without_key():
    provider = AnthropicProvider(api_key=None)
    suggestion = provider.suggest_correction_wording(defect_description="x", context="")
    assert suggestion.is_mock is True


def test_groq_provider_falls_back_without_key():
    provider = GroqProvider(api_key=None)
    suggestion = provider.suggest_correction_wording(defect_description="x", context="")
    assert suggestion.is_mock is True
