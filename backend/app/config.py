from pathlib import Path
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / "backend" / ".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "NetSol Website Chatbot"
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    frontend_dist_dir: Path = BASE_DIR / "frontend" / "dist"
    knowledge_file: Path = BASE_DIR / "Space_Exploration_RAG_Document.docx"
    knowledge_dir: Path = BASE_DIR / "backend" / "data" / "netsol_scraped"
    faiss_index_dir: Path = BASE_DIR / "backend" / "data" / "faiss_index"
    chunk_size: int = 900
    chunk_overlap: int = 180
    top_k: int = 4
    embedding_model: str = Field(
        default="gemini-embedding-001",
        validation_alias=AliasChoices("embedding_model", "gemini_embedding_model", "openai_embedding_model"),
    )
    chat_model: str = Field(
        default="gemini-2.5-flash",
        validation_alias=AliasChoices("chat_model", "gemini_chat_model", "openai_model", "openai_chat_model"),
    )
    google_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("google_api_key", "gemini_api_key", "openai_api_key"),
    )


settings = Settings()
