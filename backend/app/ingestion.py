from __future__ import annotations

import logging
from pathlib import Path

from langchain_community.document_loaders import Docx2txtLoader, PyPDFLoader, TextLoader
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .config import settings


logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".docx", ".md"}


def _get_embeddings() -> GoogleGenerativeAIEmbeddings:
    return GoogleGenerativeAIEmbeddings(
        model=settings.embedding_model,
        google_api_key=settings.google_api_key,
    )


def load_documents(path: Path) -> list[Document]:
    if path.suffix.lower() == ".pdf":
        return PyPDFLoader(str(path)).load()
    if path.suffix.lower() == ".docx":
        return Docx2txtLoader(str(path)).load()
    return TextLoader(str(path), encoding="utf-8").load()


def load_documents_from_dir(directory: Path) -> list[Document]:
    """Load all .md and .txt files from a directory."""
    all_docs: list[Document] = []
    for file in sorted(directory.glob("*.md")) + sorted(directory.glob("*.txt")):
        try:
            docs = TextLoader(str(file), encoding="utf-8").load()
            for doc in docs:
                doc.metadata["source"] = str(file)
            all_docs.extend(docs)
        except Exception as exc:
            logger.warning("Failed to load %s: %s", file, exc)
    return all_docs


def load_or_create_vector_store() -> FAISS:
    embeddings = _get_embeddings()
    index_dir = settings.faiss_index_dir

    if index_dir.exists():
        return FAISS.load_local(str(index_dir), embeddings, allow_dangerous_deserialization=True)

    knowledge_dir = settings.knowledge_dir
    if knowledge_dir is not None and knowledge_dir.exists():
        md_files = list(knowledge_dir.glob("*.md"))
        txt_files = list(knowledge_dir.glob("*.txt"))
        if md_files or txt_files:
            documents = load_documents_from_dir(knowledge_dir)
        else:
            logger.warning(
                "knowledge_dir %s exists but is empty; falling back to knowledge_file",
                knowledge_dir,
            )
            if not settings.knowledge_file.exists():
                raise FileNotFoundError(f"Knowledge file not found: {settings.knowledge_file}")
            documents = load_documents(settings.knowledge_file)
    else:
        if not settings.knowledge_file.exists():
            raise FileNotFoundError(f"Knowledge file not found: {settings.knowledge_file}")
        documents = load_documents(settings.knowledge_file)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    chunks = splitter.split_documents(documents)
    logger.info("Building FAISS index from %d chunks...", len(chunks))
    vector_store = FAISS.from_documents(chunks, embeddings)
    index_dir.mkdir(parents=True, exist_ok=True)
    vector_store.save_local(str(index_dir))
    logger.info("FAISS index saved to %s", index_dir)
    return vector_store
