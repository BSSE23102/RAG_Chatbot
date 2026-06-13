from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / "backend" / ".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "History-Aware RAG Chatbot"
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    frontend_dist_dir: Path = BASE_DIR / "frontend" / "dist"
    knowledge_file: Path = BASE_DIR / "Space_Exploration_RAG_Document.docx"
    knowledge_dir: Path = BASE_DIR / "backend" / "data" / "netsol_scraped"
    faiss_index_dir: Path = BASE_DIR / "backend" / "data" / "faiss_index"
    chunk_size: int = 900
    chunk_overlap: int = 180
    top_k: int = 4
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    groq_model: str = "llama-3.1-8b-instant"
    groq_api_key: str | None = None


settings = Settings()
