# tests/test_rag.py
import os
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="needs OPENAI_API_KEY")
def test_chain_answers_known_fact_from_pdfs():
    from chatbot.rag import build_chain

    chain = build_chain(vectorstore_dir=REPO_ROOT / "vectorstore")
    result = chain.invoke(
        {"input": "What is the maximum maternity care benefit?"},
        config={"configurable": {"session_id": "test-1"}},
    )
    answer = result["answer"]
    assert "120,000" in answer or "1,20,000" in answer or "120000" in answer


@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="needs OPENAI_API_KEY")
def test_chain_refuses_out_of_scope_question():
    from chatbot.rag import build_chain

    chain = build_chain(vectorstore_dir=REPO_ROOT / "vectorstore")
    result = chain.invoke(
        {"input": "What's the weather in Bangalore today?"},
        config={"configurable": {"session_id": "test-2"}},
    )
    answer = result["answer"].lower()
    assert "don't have that information" in answer or "do not have" in answer


@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="needs OPENAI_API_KEY")
def test_chain_uses_history_for_followup():
    from chatbot.rag import build_chain

    chain = build_chain(vectorstore_dir=REPO_ROOT / "vectorstore")
    cfg = {"configurable": {"session_id": "test-3"}}
    chain.invoke({"input": "Tell me about parental bonding leave for full-time employees."}, config=cfg)
    follow = chain.invoke({"input": "And for limited-term employees?"}, config=cfg)
    answer = follow["answer"]
    assert "16" in answer  # 16 weeks for LTE
