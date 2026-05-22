import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")


class Config:
    # LLM
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "gpt-oss-120b")

    # Embeddings
    EMBEDDER_PATH: str = os.getenv("EMBEDDER_PATH", "C:/Users/zheny/.cache/huggingface/hub/"
    "models--intfloat--multilingual-e5-base/snapshots/"
    "835193815a3936a24a0ee7dc9e3d48c1fbb19c55")

    # Qdrant
    QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", "6333"))

    # RAG
    TOP_K: int = int(os.getenv("TOP_K", "5"))
    BM25_TOP_K: int = int(os.getenv("BM25_TOP_K", "15"))
    E5_TOP_K: int = int(os.getenv("E5_TOP_K", "15"))
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "800"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "150"))


cfg = Config()
