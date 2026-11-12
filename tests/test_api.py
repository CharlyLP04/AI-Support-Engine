from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_traditional_api_uses_shared_response_contract():
    response = client.post(
        "/api/analyze",
        json={"message": "No puedo iniciar sesión", "mode": "traditional"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["category"] == "ACCESS"
    assert body["priority"] == "MEDIUM"
    assert body["response"]
    assert body["requiresHumanReview"] is False
    assert body["mode"] == "traditional"


def test_api_rejects_empty_message():
    response = client.post("/api/analyze", json={"message": "   ", "mode": "traditional"})

    assert response.status_code == 422


def test_api_rejects_unknown_mode():
    response = client.post("/api/analyze", json={"message": "No puedo entrar", "mode": "rules"})

    assert response.status_code == 422


def test_generative_provider_failure_returns_safe_error(monkeypatch):
    def fail(_message):
        raise RuntimeError("upstream unavailable with credential=secret-value")

    monkeypatch.setattr("app.main.analyze_generative", fail)
    response = client.post(
        "/api/analyze",
        json={"message": "No puedo iniciar sesión", "mode": "generative"},
    )

    assert response.status_code == 502
    assert "secret-value" not in response.text


import pytest


@pytest.mark.parametrize("payload", [
    {}, {"message": "hola"},
    {"message": 123, "mode": "traditional"},
    {"message": "x" * 4001, "mode": "traditional"},
    {"message": "hola", "mode": "traditional", "extra": True},
])
def test_invalid_requests_never_call_provider(monkeypatch, payload):
    monkeypatch.setattr("app.main.analyze_generative", lambda _: pytest.fail("Unexpected provider call"))
    assert client.post("/api/analyze", json=payload).status_code == 422


@pytest.mark.parametrize("failure", ["timeout", "http", "envelope", "json"])
def test_provider_failures_return_502_without_payload(monkeypatch, failure):
    import httpx

    def post(*args, **kwargs):
        if failure == "timeout":
            raise httpx.ReadTimeout("secret-upstream-value")
        if failure == "http":
            return httpx.Response(503, text="secret-upstream-value")
        if failure == "envelope":
            return httpx.Response(200, json={"error": "secret-upstream-value"})
        return httpx.Response(200, json={"choices": [{"message": {"content": "secret-upstream-value"}}]})

    monkeypatch.setenv("HERMES_PROXY_URL", "http://127.0.0.1:8645/v1")
    monkeypatch.setattr("app.generative.httpx.post", post)
    result = client.post("/api/analyze", json={"message": "No puedo entrar", "mode": "generative"})
    assert result.status_code == 502
    assert "secret-upstream-value" not in result.text
