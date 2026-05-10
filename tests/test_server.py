# tests/test_server.py
import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def client():
    from chatbot.server import app
    return TestClient(app)


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "vectorstore_loaded" in body


@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="needs OPENAI_API_KEY")
def test_chat_returns_answer_with_session_id(client):
    r = client.post(
        "/chat",
        json={"session_id": "srv-1", "message": "How many AI Fellow vacancies are there?"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["session_id"] == "srv-1"
    assert isinstance(body["response"], str) and body["response"]
    assert "5" in body["response"] or "five" in body["response"].lower()


def test_chat_rejects_missing_message(client):
    r = client.post("/chat", json={"session_id": "srv-2"})
    assert r.status_code == 422
