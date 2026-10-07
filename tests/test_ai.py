from types import SimpleNamespace

import pytest

from app.services.ai import AIServiceError, generate_feedback


def response_with(content):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


def test_ai_malformed_json_retries_once_then_fails(monkeypatch):
    calls = []

    class Completions:
        def create(self, **kwargs):
            calls.append(kwargs)
            return response_with("not-json")

    client = SimpleNamespace(chat=SimpleNamespace(completions=Completions()))
    monkeypatch.setattr("app.services.ai._get_client", lambda: client)
    with pytest.raises(AIServiceError, match="malformed feedback"):
        generate_feedback("resume", [], [], 40)
    assert len(calls) == 2


def test_ai_provider_failure_is_controlled(monkeypatch):
    class Completions:
        def create(self, **kwargs):
            raise ConnectionError("secret provider failure")

    client = SimpleNamespace(chat=SimpleNamespace(completions=Completions()))
    monkeypatch.setattr("app.services.ai._get_client", lambda: client)
    with pytest.raises(AIServiceError, match="provider is unavailable"):
        generate_feedback("resume", [], [], 40)


def test_ai_valid_response_is_validated(monkeypatch):
    content = '{"summary":"ok","strengths":[],"weaknesses":[],"recommendation":"yes"}'
    client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=lambda **kwargs: response_with(content))
        )
    )
    monkeypatch.setattr("app.services.ai._get_client", lambda: client)
    assert generate_feedback("resume", [], [], 40)["summary"] == "ok"
