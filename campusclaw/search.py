from __future__ import annotations

import re

from flask import Blueprint, g, request

from .auth import auth_required
from .db import search_chunks_by_fts, search_chunks_by_like
from .http import ApiError, api_response

bp = Blueprint("search", __name__, url_prefix="/api/v1")


def query_terms(query: str, limit: int = 24) -> list[str]:
    terms: list[str] = []
    for raw in query.split():
        compact = re.sub(r"[^\w\u4e00-\u9fff]", "", raw)
        if len(compact) < 3:
            continue
        terms.append(compact)
        terms.extend(compact[index : index + 3] for index in range(len(compact) - 2))
    return list(dict.fromkeys(terms))[:limit]


def make_snippet(content: str, query: str, radius: int = 90) -> str:
    compact = " ".join(content.split())
    candidates = sorted(query_terms(query), key=len, reverse=True) + [query]
    position = next(
        (
            compact.lower().find(candidate.lower())
            for candidate in candidates
            if compact.lower().find(candidate.lower()) >= 0
        ),
        -1,
    )
    if position < 0:
        return compact[: radius * 2] + ("…" if len(compact) > radius * 2 else "")
    start = max(0, position - radius)
    end = min(len(compact), position + len(query) + radius)
    return ("…" if start else "") + compact[start:end] + ("…" if end < len(compact) else "")


def search(class_id: str, query: str, limit: int) -> list[dict[str, object]]:
    terms = query_terms(query)
    fts_query = " OR ".join(f'"{term.replace(chr(34), chr(34) * 2)}"' for term in terms)
    rows = search_chunks_by_fts(class_id, fts_query, limit) if fts_query else []
    if not rows:
        rows = search_chunks_by_like(class_id, terms[:12] or [query], limit)
    return [
        {
            "chunk_id": row["id"],
            "material_id": row["material_id"],
            "title": row["title"],
            "chunk_index": row["chunk_index"],
            "start_line": row["start_line"],
            "end_line": row["end_line"],
            "snippet": make_snippet(row["content"], query),
            "score": round(float(row["rank"]), 6),
        }
        for row in rows
    ]


@bp.get("/search")
@auth_required()
def find() -> tuple:
    query = request.args.get("q", "").strip()
    if not query or len(query) > 200:
        raise ApiError(code=1101, message="查询词长度必须为 1 到 200 个字符", status=400)
    try:
        limit = int(request.args.get("limit", "8"))
    except ValueError as error:
        raise ApiError(code=1101, message="limit 必须是整数", status=400) from error
    if not 1 <= limit <= 20:
        raise ApiError(code=1101, message="limit 必须在 1 到 20 之间", status=400)
    return api_response({"items": search(g.user["class_id"], query, limit)})
