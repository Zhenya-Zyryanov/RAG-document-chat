from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File
from qdrant_client.models import Filter, FieldCondition, MatchValue
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from session_manager import create_session, delete_session, list_sessions, add_document, get_qdrant, remove_document
from session_manager import META_COLLECTION, _ensure_meta_collection
from rag_pipeline import rag_pipeline

app = FastAPI(
    title="API like NotebookLM",
    description="Local RAG over uploaded documents. Session-based.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:6767", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

class CreateSessionRequest(BaseModel):
    name: str

class AskRequest(BaseModel):
    query: str


"""@app.get("/health", tags=["system"])
def health():
    try:
        qdrant = get_qdrant()
        collections = qdrant.get_collections().collections
        return {"status": "ok", "qdrant_collections": len(collections)}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Qdrant недоступен: {e}")
"""

@app.get("/sessions", tags=["sessions"])
def get_sessions():
    sessions = list_sessions()
    return {
        "count": len(sessions),
        "sessions": [
            {
                "session_id": s.session_id,
                "name": s.name,
                "created_at": s.created_at,
                "documents": s.documents,
                "doc_count": len(s.documents),
            }
            for s in sessions
        ],
    }


@app.post("/sessions", status_code=201, tags=["sessions"])
def post_session(body: CreateSessionRequest):
    if not body.name.strip():
        raise HTTPException(status_code=422, detail="Название сессии не может быть пустым")
    session_info = create_session(body.name.strip())
    return {
        "session_id": session_info.session_id,
        "name": session_info.name,
        "created_at": session_info.created_at,
        "documents": session_info.documents,
    }


@app.delete("/sessions/{session_id}", tags=["sessions"])
def delete_session_endpoint(session_id: str):
    _require_session(session_id)
    delete_session(session_id)
    return {"deleted": session_id}


ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx", ".csv", ".xlsx", ".xls"}


@app.post("/sessions/{session_id}/documents", status_code=201, tags=["documents"])
async def upload_document(session_id: str, file: UploadFile = File(...)):
    _require_session(session_id)

    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Формат '{suffix}' не поддерживается. Допустимые: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Сохраняем во временный файл — add_document читает с диска
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    # Переименовываем чтобы doc_id получился из оригинального имени
    named_path = tmp_path.parent / file.filename
    tmp_path.rename(named_path)

    try:
        doc_id = add_document(session_id, named_path)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    finally:
        named_path.unlink(missing_ok=True)

    return {
        "doc_id":   doc_id,
        "filename": file.filename,
        "session_id": session_id,
    }


@app.get("/sessions/{session_id}/documents", tags=["documents"])
def get_documents(session_id: str):
    qdrant = get_qdrant()
    # Убедимся, что коллекция метаданных есть
    try:
        qdrant.get_collection(META_COLLECTION)
    except Exception:
        _ensure_meta_collection()
    results, _ = qdrant.scroll(
        collection_name=META_COLLECTION,
        scroll_filter=Filter(must=[FieldCondition(key="session_id", match=MatchValue(value=session_id))]),
        limit=1,
        with_payload=True,
    )
    if not results:
        raise HTTPException(status_code=404, detail="Сессия не найдена")
    docs_payload = results[0].payload.get("documents", [])
    docs_info = []
    for item in docs_payload:
        if isinstance(item, dict):
            docs_info.append({"doc_id": item["doc_id"], "filename": item["filename"]})
        else:
            docs_info.append({"doc_id": Path(item).stem[:40], "filename": item})
    return {"session_id": session_id, "documents": docs_info, "count": len(docs_info)}


@app.delete("/sessions/{session_id}/documents/{doc_id}", tags=["documents"])
def delete_document(session_id: str, doc_id: str):
    _require_session(session_id)
    try:
        remove_document(session_id, doc_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"deleted_doc_id": doc_id, "session_id": session_id}


@app.post("/sessions/{session_id}/ask", tags=["rag"])
def ask(session_id: str, body: AskRequest):
    _require_session(session_id)

    if not body.query.strip():
        raise HTTPException(status_code=422, detail="Запрос не может быть пустым")

    try:
        result = rag_pipeline(body.query.strip(), session_id)
    except ValueError as e:
        # Сессия пустая — нет документов
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ошибка LLM: {e}")

    return {
        "query": result["query"],
        "answer": result["answer"],
        "latency_ms": result["latency_ms"],
        "retrieval_ms": result["retrieval_ms"],
        "llm_ms": result["llm_ms"],
        "tokens": result["tokens"],
        "sources": [
            {
                "doc_id": c["doc_id"],
                "chunk_id": c["chunk_id"],
                "source_file": c.get("source_file", ""),
                "score": round(c["score"], 5),
                "text": c["text"],
            }
            for c in result["sources"]
        ],
    }


def _require_session(session_id: str):
    sessions = {s.session_id for s in list_sessions()}
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail=f"Сессия не найдена: {session_id}")

from app.main import app as test_app
from fastapi.routing import APIRouter

test_router = APIRouter()
test_router.routes = test_app.routes
app.include_router(test_router)
# -----------------------------------------------------------

from fastapi.staticfiles import StaticFiles
dist_path = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if dist_path.exists():
    app.mount("/", StaticFiles(directory=dist_path, html=True), name="static")