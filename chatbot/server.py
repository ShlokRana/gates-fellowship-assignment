"""FastAPI app exposing the RAG chatbot."""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

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


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    def index():
        return FileResponse(str(STATIC_DIR / "index.html"))
