import shutil
import os
import sys
from pathlib import Path

# Add current directory to path to ensure app module can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.config import settings
from app.ingestion import load_or_create_vector_store

def main():
    index_dir = settings.faiss_index_dir
    print(f"Target FAISS index directory: {index_dir}")

    if index_dir.exists():
        print(f"Deleting existing FAISS index at {index_dir} to rebuild with new embedding dimensions...")
        try:
            shutil.rmtree(index_dir)
            print("Successfully deleted old FAISS index.")
        except Exception as e:
            print(f"Error deleting old index: {e}")

    print("Initializing FAISS vector store creation...")
    try:
        vector_store = load_or_create_vector_store()
        print("FAISS vector store successfully created and saved!")
    except Exception as e:
        print(f"Error during ingestion: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
