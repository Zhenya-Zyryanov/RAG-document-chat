from __future__ import annotations
from sentence_transformers import SentenceTransformer
import numpy as np
from config import cfg


_model: SentenceTransformer | None = None


def get_embedder() -> SentenceTransformer:
    global _model
    if _model is None:
        print(f"[embedder] Загрузка модели: {cfg.EMBEDDER_PATH}")
        _model = SentenceTransformer(cfg.EMBEDDER_PATH)
        print("[embedder] Готово.")
    return _model


def encode_passages(texts: list[str]) -> np.ndarray:
    model = get_embedder()
    return model.encode(
        [f"passage: {t}" for t in texts],
        normalize_embeddings=True,
        show_progress_bar=False,
        batch_size=32,
    )


def encode_query(query: str) -> np.ndarray:
    model = get_embedder()
    return model.encode(
        [f"query: {query}"],
        normalize_embeddings=True,
        show_progress_bar=False,
    )[0]