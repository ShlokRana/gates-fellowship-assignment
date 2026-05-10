"""FastAPI app exposing the RAG chatbot."""
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Any

from chatbot.rag import build_chain

REPO_ROOT = Path(__file__).resolve().parent.parent
VECTORSTORE_DIR = REPO_ROOT / "vectorstore"
STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="Gates Foundation AI Fellowship FAQ Bot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_chain = None


def _get_chain():
    global _chain
    if _chain is None:
        if not VECTORSTORE_DIR.exists():
            raise HTTPException(
                status_code=503,
                detail="vectorstore not built. Run: python -m chatbot.ingest",
            )
        _chain = build_chain(VECTORSTORE_DIR)
    return _chain


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    session_id: str
    response: str
    sources: list[str]


@app.get("/healthz")
def healthz():
    return {
        "status": "ok",
        "vectorstore_loaded": VECTORSTORE_DIR.exists(),
    }


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    chain = _get_chain()
    result = chain.invoke(
        {"input": req.message},
        config={"configurable": {"session_id": req.session_id}},
    )
    sources = []
    for d in result.get("context", []):
        meta = d.metadata or {}
        src = meta.get("source", "unknown")
        page = meta.get("page")
        sources.append(f"{Path(src).name} p.{page}" if page is not None else Path(src).name)
    return ChatResponse(
        session_id=req.session_id,
        response=result["answer"],
        sources=sources,
    )


class OAIMessage(BaseModel):
    role: str
    content: str

class OAIRequest(BaseModel):
    messages: list[OAIMessage]
    model: str = "fellowship-faq"
    temperature: float = 0
    stream: bool = False

@app.post("/v1/chat/completions")
def oai_chat(req: OAIRequest):
    """OpenAI-compatible endpoint so CeRAI's LOCAL provider can call us."""
    user_msg = next(
        (m.content for m in reversed(req.messages) if m.role == "user"), ""
    )
    if not user_msg:
        raise HTTPException(status_code=400, detail="No user message found")

    chain = _get_chain()
    session_id = str(uuid.uuid4())
    result = chain.invoke(
        {"input": user_msg},
        config={"configurable": {"session_id": session_id}},
    )
    answer = result["answer"]
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": req.model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": answer}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    def index():
        return FileResponse(str(STATIC_DIR / "index.html"))
