from __future__ import annotations

from pathlib import Path
import threading
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.models import ChatRequest, ChatResponse, SourceChunk
from app.session_store import session_store

app = FastAPI(title=settings.app_name)
rag_service: Any = None
rag_service_lock = threading.Lock()
rag_service_ready = threading.Event()
rag_initialization_error: Exception | None = None


def initialize_rag_service_bg() -> None:
    global rag_service, rag_initialization_error
    try:
        from app.ingestion import load_or_create_vector_store
        from app.rag import RAGService

        vector_store = load_or_create_vector_store()
        service = RAGService(vector_store)
        with rag_service_lock:
            rag_service = service
        rag_service_ready.set()
    except Exception as e:
        import logging
        logging.getLogger("uvicorn").error(f"Failed to initialize RAG service in background: {e}", exc_info=True)
        rag_initialization_error = e
        rag_service_ready.set()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event() -> None:
    threading.Thread(target=initialize_rag_service_bg, daemon=True).start()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    global rag_service
    # Wait for the service to initialize (up to 60 seconds)
    ready = rag_service_ready.wait(timeout=60.0)
    if not ready:
        raise HTTPException(status_code=503, detail="RAG service is still initializing. Please try again in a moment.")

    if rag_service is None:
        error_detail = "RAG service failed to initialize."
        if rag_initialization_error:
            error_detail += f" Error: {rag_initialization_error}"
        raise HTTPException(status_code=500, detail=error_detail)

    from langchain_core.messages import AIMessage, HumanMessage

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
