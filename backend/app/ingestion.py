from __future__ import annotations

import logging
from pathlib import Path

from langchain_community.document_loaders import Docx2txtLoader, PyPDFLoader, TextLoader
from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sklearn.feature_extraction.text import HashingVectorizer

from .config import settings


logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".docx"}


class HashingEmbeddings(Embeddings):
    def __init__(self, n_features: int = 1024) -> None:
        self.vectorizer = HashingVectorizer(n_features=n_features, alternate_sign=False, norm="l2")

    def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        matrix = self.vectorizer.transform(texts)
        return matrix.astype("float32").toarray().tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed_texts(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._embed_texts([text])[0]


def load_documents(path: Path) -> list[Document]:
    if path.suffix.lower() == ".pdf":
        return PyPDFLoader(str(path)).load()
    if path.suffix.lower() == ".docx":
        return Docx2txtLoader(str(path)).load()
    return TextLoader(str(path), encoding="utf-8").load()


def load_documents_from_dir(directory: Path) -> list[Document]:
    """Load all .md and .txt files from a directory, returning successfully loaded documents."""
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
    embeddings = HashingEmbeddings()
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
                "knowledge_dir %s exists but contains no .md or .txt files; falling back to knowledge_file",
                knowledge_dir,
            )
            if not settings.knowledge_file.exists():
                raise FileNotFoundError(f"Knowledge file not found: {settings.knowledge_file}")
            documents = load_documents(settings.knowledge_file)
    else:
        if not settings.knowledge_file.exists():
            raise FileNotFoundError(f"Knowledge file not found: {settings.knowledge_file}")
        documents = load_documents(settings.knowledge_file)

    splitter = RecursiveCharacterTextSplitter(chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap)
    chunks = splitter.split_documents(documents)
    vector_store = FAISS.from_documents(chunks, embeddings)
    index_dir.mkdir(parents=True, exist_ok=True)
    vector_store.save_local(str(index_dir))
    return vector_store
