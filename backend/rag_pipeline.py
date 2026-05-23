"""
rag_pipeline.py — Hybrid BM25 + E5 RAG с RRF fusion.
Без Langfuse, без LiteLLM — чистый OpenAI клиент.
"""

from __future__ import annotations

import re
import time
import numpy as np
from openai import OpenAI
from nltk.stem.snowball import RussianStemmer

from backend.config import cfg
from backend.embedder import encode_query
from session_manager import SessionContext, get_session_context


llm = OpenAI(base_url=cfg.LLM_BASE_URL, api_key=cfg.LLM_API_KEY)


_stemmer = RussianStemmer()


def _normalize(text: str) -> list[str]:
    return [_stemmer.stem(w) for w in re.findall(r"\w+", text.lower())]


def retrieve(query: str, ctx: SessionContext) -> list[dict]:
    chunks = ctx.chunks

    # BM25: токенизируем + стеммируем, получаем скоры по всем чанкам
    bm25_scores = ctx.bm25.get_scores(_normalize(query))
    bm25_top = [
        {**chunks[i], "bm25_rank": rank + 1}
        for rank, i in enumerate(np.argsort(bm25_scores)[::-1][:cfg.BM25_TOP_K])
    ]

    # E5: кодируем запрос, dot product с матрицей чанков
    q_emb = encode_query(query)
    e5_scores = np.dot(ctx.chunk_embeddings, q_emb)
    e5_top = [
        {**chunks[i], "e5_rank": rank + 1, "e5_score": float(e5_scores[i])}
        for rank, i in enumerate(np.argsort(e5_scores)[::-1][:cfg.E5_TOP_K])
    ]

    merged: dict[str, dict] = {}
    for r in bm25_top:
        merged[r["chunk_id"]] = {**r, "e5_rank": None, "e5_score": None}
    for r in e5_top:
        cid = r["chunk_id"]
        if cid not in merged:
            merged[cid] = {**r, "bm25_rank": None}
        else:
            merged[cid]["e5_rank"] = r["e5_rank"]
            merged[cid]["e5_score"] = r["e5_score"]

    for item in merged.values():
        item["score"] = (
            (1 / (60 + item["bm25_rank"]) if item.get("bm25_rank") else 0.0)
            + (1 / (60 + item["e5_rank"])  if item.get("e5_rank")   else 0.0)
        )

    return sorted(merged.values(), key=lambda x: x["score"], reverse=True)[:cfg.TOP_K]


def build_prompt(query: str, contexts: list[dict]) -> str:
    ctx_lines = "\n".join(
        f"[{i+1}] (doc: {c['doc_id']}) (файл: {c.get('source_file', '?')}) {c['text']}"
        for i, c in enumerate(contexts)
    )
    return (
        f"Контекст:\n{ctx_lines}\n\n"
        f"Вопрос: {query}\n\n"
        "Правила:\n"
        "- Отвечай строго на основе контекста\n"
        "- Если информации нет — ответь 'Не найдено'\n"
        "- Указывай источники: doc_id и имя файла\n\n"
        "Ответ:"
    )


def rag_pipeline(query: str, session_id: str) -> dict:
    ctx = get_session_context(session_id)

    t0 = time.perf_counter()
    chunks = retrieve(query, ctx)
    retrieval_ms = round((time.perf_counter() - t0) * 1000)

    prompt = build_prompt(query, chunks)

    t1 = time.perf_counter()
    response = llm.chat.completions.create(
        model=cfg.MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    llm_ms = round((time.perf_counter() - t1) * 1000)

    answer = response.choices[0].message.content.strip()
    usage  = response.usage

    return {
        "query": query,
        "answer": answer,
        "sources": chunks,
        "latency_ms": round((time.perf_counter() - t0) * 1000),
        "retrieval_ms": retrieval_ms,
        "llm_ms": llm_ms,
        "tokens": {
            "prompt": usage.prompt_tokens,
            "completion": usage.completion_tokens,
            "total": usage.total_tokens,
        },
    }