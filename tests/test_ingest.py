# tests/test_ingest.py
import os
import shutil
from pathlib import Path
import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
VECTORSTORE_DIR = REPO_ROOT / "vectorstore"


@pytest.fixture
def clean_vectorstore():
    if VECTORSTORE_DIR.exists():
        shutil.rmtree(VECTORSTORE_DIR)
    yield VECTORSTORE_DIR


@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="needs OPENAI_API_KEY")
def test_ingest_creates_vectorstore_and_retrieves_known_fact(clean_vectorstore):
    from chatbot.ingest import build_vectorstore
    from langchain_community.vectorstores import FAISS
    from langchain_openai import OpenAIEmbeddings

    build_vectorstore(
        data_dir=REPO_ROOT / "data",
        out_dir=clean_vectorstore,
    )

    assert (clean_vectorstore / "index.faiss").exists()
    assert (clean_vectorstore / "index.pkl").exists()

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    store = FAISS.load_local(
        str(clean_vectorstore), embeddings, allow_dangerous_deserialization=True
    )
    hits = store.similarity_search("maternity care benefit", k=3)
    assert any("maternity" in d.page_content.lower() for d in hits)
