from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from langchain_core.messages import AIMessage, HumanMessage

from app.config import settings
from app.ingestion import load_or_create_vector_store
from app.models import ChatRequest, ChatResponse, SourceChunk
from app.rag import RAGService
from app.session_store import session_store

app = FastAPI(title=settings.app_name)
rag_service: RAGService | None = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event() -> None:
    global rag_service
    vector_store = load_or_create_vector_store()
    rag_service = RAGService(vector_store)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    if rag_service is None:
        raise HTTPException(status_code=503, detail="RAG service is not ready")

    history = session_store.get_history(request.session_id)
    result = rag_service.answer(request.message, history.messages)
    answer = result.get("answer", "")
    source_documents = result.get("context", [])

    history.add_messages([HumanMessage(content=request.message), AIMessage(content=answer)])
    source_chunks = [
        SourceChunk(
            content=document.page_content,
            source=document.metadata.get("source"),
            score=document.metadata.get("score"),
        )
        for document in source_documents
    ]
    return ChatResponse(session_id=request.session_id, answer=answer, sources=source_chunks, history=session_store.snapshot(request.session_id))


frontend_dist = settings.frontend_dist_dir
assets_dir = frontend_dist / "assets"
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")


@app.get("/")
def root() -> FileResponse:
    index_file = frontend_dist / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return FileResponse(Path(__file__).parent / "static" / "index.html")
