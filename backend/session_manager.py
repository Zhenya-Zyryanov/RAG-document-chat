from __future__ import annotations

import uuid
import re
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)
from rank_bm25 import BM25Okapi
from nltk.stem.snowball import RussianStemmer
from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.config import cfg
from backend.document_loader import load_document
from backend.embedder import encode_passages


VECTOR_DIM = 768
COLLECTION_PREFIX = "session_"
META_COLLECTION = "notebooklm_meta"


_qdrant: QdrantClient | None = None


def get_qdrant() -> QdrantClient:
    global _qdrant
    if _qdrant is None:
        _qdrant = QdrantClient(host=cfg.QDRANT_HOST, port=cfg.QDRANT_PORT)
    return _qdrant


_bm25_cache: dict[str, dict] = {}

stemmer = RussianStemmer()
splitter = RecursiveCharacterTextSplitter(
    chunk_size=cfg.CHUNK_SIZE,
    chunk_overlap=cfg.CHUNK_OVERLAP,
    separators=["\n\n", "\n", ". ", " ", ""],
    length_function=len,
)


@dataclass
class SessionInfo:
    session_id: str
    name: str
    created_at: str
    documents: list[dict] = field(default_factory=list)

@dataclass
class SessionContext:
    session_id: str
    bm25: BM25Okapi
    chunks: list[dict]
    chunk_embeddings: np.ndarray


def _normalize(text: str) -> list[str]:
    return [stemmer.stem(w) for w in re.findall(r"\w+", text.lower())]


def _collection_name(session_id: str) -> str:
    return f"{COLLECTION_PREFIX}{session_id}"


def _ensure_meta_collection():
    qdrant = get_qdrant()
    existing = {c.name for c in qdrant.get_collections().collections}
    if META_COLLECTION not in existing:
        qdrant.create_collection(
            META_COLLECTION,
            vectors_config=VectorParams(size=1, distance=Distance.COSINE),
        )


def _save_session_meta(info: SessionInfo):
    qdrant = get_qdrant()
    _ensure_meta_collection()
    qdrant.upsert(
        collection_name=META_COLLECTION,
        points=[
            PointStruct(
                id=_str_to_uuid_int(info.session_id),
                vector=[0.0],
                payload={
                    "session_id": info.session_id,
                    "name": info.name,
                    "created_at": info.created_at,
                    "documents": info.documents,
                },
            )
        ],
    )


def _str_to_uuid_int(s) -> int:
    return uuid.UUID(s).int % (2**63)



def create_session(name: str) -> SessionInfo:
    session_id = str(uuid.uuid4())
    qdrant = get_qdrant()

    qdrant.create_collection(
        collection_name=_collection_name(session_id),
        vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
    )

    info = SessionInfo(
        session_id=session_id,
        name=name,
        created_at=datetime.now().isoformat(timespec="seconds"),
        documents=[],
    )
    _save_session_meta(info)

    _bm25_cache[session_id] = {"bm25": None, "chunks": []}

    print(f"[session] Создана сессия '{name}' ({session_id})")
    return info   # вместо return session_id


def delete_session(session_id: str):
    qdrant = get_qdrant()

    col = _collection_name(session_id)
    existing = {c.name for c in qdrant.get_collections().collections}
    if col in existing:
        qdrant.delete_collection(col)

    _ensure_meta_collection()
    qdrant.delete(
        collection_name=META_COLLECTION,
        points_selector=[_str_to_uuid_int(session_id)],
    )

    _bm25_cache.pop(session_id, None)

    print(f"[session] Удалена сессия {session_id}")


def list_sessions() -> list[SessionInfo]:
    qdrant = get_qdrant()
    _ensure_meta_collection()

    results, _ = qdrant.scroll(
        collection_name=META_COLLECTION,
        limit=1000,
        with_payload=True,
        with_vectors=False,
    )

    sessions = []
    for point in results:
        p = point.payload
        docs_raw = p.get("documents", [])
        docs_list = [d["filename"] if isinstance(d, dict) else d for d in docs_raw]
        sessions.append(SessionInfo(
            session_id=p["session_id"],
            name=p["name"],
            created_at=p["created_at"],
            documents=docs_list,
        ))

    return sorted(sessions, key=lambda s: s.created_at, reverse=True)


def add_document(session_id: str, file_path: str | Path) -> str:
    path = Path(file_path)
    doc_id = path.stem[:40]

    print(f"[session] Загрузка '{path.name}' → сессия {session_id[:8]}...")

    text = load_document(path)
    if not text:
        raise ValueError(f"Документ пуст или не удалось извлечь текст: {path.name}")

    raw_chunks = splitter.split_text(text)
    chunks = []
    for i, part in enumerate(raw_chunks):
        part = part.strip().lstrip(". ").strip()
        if part:
            chunks.append({
                "doc_id": doc_id,
                "chunk_id": f"{doc_id}_{i}",
                "text": part,
                "source_file": path.name,
            })

    if not chunks:
        raise ValueError(f"Не удалось создать чанки из документа: {path.name}")

    print(f"[session] Чанков: {len(chunks)}")

    # 3. Эмбеддинги
    texts = [c["text"] for c in chunks]
    embeddings = encode_passages(texts)

    # 4. Загружаем в Qdrant
    qdrant = get_qdrant()
    col = _collection_name(session_id)

    # Генерируем уникальные integer ID для точек
    points = []
    for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        point_id = abs(hash(chunk["chunk_id"])) % (2**63)
        points.append(PointStruct(
            id=point_id,
            vector=emb.tolist(),
            payload={
                "chunk_id": chunk["chunk_id"],
                "doc_id": chunk["doc_id"],
                "text": chunk["text"],
                "source_file": chunk["source_file"],
            },
        ))

    qdrant.upsert(collection_name=col, points=points)

    # 5. Обновляем BM25 in-memory
    _rebuild_bm25(session_id)

    # 6. Обновляем метаданные сессии
    _add_doc_meta(session_id, doc_id, path.name)

    print(f"[session] ✓ Документ '{path.name}' загружен ({len(chunks)} чанков)")
    return doc_id


def _rebuild_bm25(session_id: str):
    """Перестраивает BM25 индекс из Qdrant для данной сессии."""
    qdrant = get_qdrant()
    col = _collection_name(session_id)

    all_chunks = []
    offset = None
    while True:
        results, next_offset = qdrant.scroll(
            collection_name=col,
            limit=500,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        for point in results:
            all_chunks.append({
                "chunk_id": point.payload["chunk_id"],
                "doc_id": point.payload["doc_id"],
                "text": point.payload["text"],
                "source_file": point.payload.get("source_file", ""),
            })
        if next_offset is None:
            break
        offset = next_offset

    if all_chunks:
        tokenized = [_normalize(c["text"]) for c in all_chunks]
        bm25 = BM25Okapi(tokenized)
    else:
        bm25 = None

    _bm25_cache[session_id] = {"bm25": bm25, "chunks": all_chunks}


def get_session_context(session_id: str) -> SessionContext:
    if session_id not in _bm25_cache or _bm25_cache[session_id]["bm25"] is None:
        _rebuild_bm25(session_id)

    cache = _bm25_cache[session_id]
    chunks = cache["chunks"]

    if not chunks:
        raise ValueError(f"Сессия {session_id} пустая — загрузите документы.")

    qdrant = get_qdrant()
    col = _collection_name(session_id)

    all_vectors = []
    offset = None
    chunk_order = {c["chunk_id"]: i for i, c in enumerate(chunks)}

    vectors_map = {}
    while True:
        results, next_offset = qdrant.scroll(
            collection_name=col,
            limit=500,
            offset=offset,
            with_payload=True,
            with_vectors=True,
        )
        for point in results:
            vectors_map[point.payload["chunk_id"]] = point.vector
        if next_offset is None:
            break
        offset = next_offset

    embeddings = np.array([
        vectors_map[c["chunk_id"]] for c in chunks
    ], dtype=np.float32)

    return SessionContext(
        session_id=session_id,
        bm25=cache["bm25"],
        chunks=chunks,
        chunk_embeddings=embeddings,
    )


def remove_document(session_id: str, doc_id: str):
    qdrant = get_qdrant()
    col = _collection_name(session_id)

    # 1. Удаляем чанки из Qdrant
    qdrant.delete(
        collection_name=col,
        points_selector=Filter(
            must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
        ),
    )

    # 2. Обновляем метаданные (поддерживаем и старые строки, и новые dict)
    _ensure_meta_collection()
    results, _ = qdrant.scroll(
        collection_name=META_COLLECTION,
        scroll_filter=Filter(must=[FieldCondition(key="session_id", match=MatchValue(value=session_id))]),
        limit=1,
        with_payload=True,
    )
    if not results:
        raise ValueError("Метаданные сессии не найдены")

    point = results[0]
    docs = point.payload.get("documents", [])
    new_docs = []
    found = False
    for item in docs:
        if isinstance(item, dict):
            if item["doc_id"] != doc_id:
                new_docs.append(item)
            else:
                found = True
        else:
            if Path(item).stem[:40] != doc_id:
                new_docs.append(item)
            else:
                found = True

    if not found:
        raise ValueError(f"Документ с doc_id '{doc_id}' не найден в сессии")

    qdrant.set_payload(
        collection_name=META_COLLECTION,
        payload={"documents": new_docs},
        points=[point.id],
    )

    # 3. Перестраиваем BM25
    _rebuild_bm25(session_id)
    print(f"[session] Удалён документ '{doc_id}' из сессии {session_id[:8]}")

def _add_doc_meta(session_id: str, doc_id: str, filename: str):
    qdrant = get_qdrant()
    _ensure_meta_collection()
    results, _ = qdrant.scroll(
        collection_name=META_COLLECTION,
        scroll_filter=Filter(
            must=[FieldCondition(key="session_id", match=MatchValue(value=session_id))]
        ),
        with_payload=True,
        limit=1,
    )
    if not results:
        return
    point = results[0]
    docs = point.payload.get("documents", [])
    # проверка на дубликат
    if not any(d["doc_id"] == doc_id for d in docs):
        docs.append({"doc_id": doc_id, "filename": filename})
    qdrant.set_payload(
        collection_name=META_COLLECTION,
        payload={"documents": docs},
        points=[point.id],
    )