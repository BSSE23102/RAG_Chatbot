from __future__ import annotations

from pathlib import Path

from langchain_community.document_loaders import Docx2txtLoader, PyPDFLoader, TextLoader
from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sklearn.feature_extraction.text import HashingVectorizer

from .config import settings


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


def load_or_create_vector_store() -> FAISS:
    embeddings = HashingEmbeddings()
    index_dir = settings.faiss_index_dir
    if index_dir.exists():
        return FAISS.load_local(str(index_dir), embeddings, allow_dangerous_deserialization=True)

    if not settings.knowledge_file.exists():
        raise FileNotFoundError(f"Knowledge file not found: {settings.knowledge_file}")

    documents = load_documents(settings.knowledge_file)
    splitter = RecursiveCharacterTextSplitter(chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap)
    chunks = splitter.split_documents(documents)
    vector_store = FAISS.from_documents(chunks, embeddings)
    index_dir.mkdir(parents=True, exist_ok=True)
    vector_store.save_local(str(index_dir))
    return vector_store
