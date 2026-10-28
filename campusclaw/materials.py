from __future__ import annotations

import uuid
from collections.abc import Iterator
from pathlib import Path

from flask import Blueprint, current_app, g, request

from .auth import auth_required
from .db import create_material, get_material_for_class, list_chunks, list_materials
from .http import ApiError, api_response, not_found

bp = Blueprint("materials", __name__, url_prefix="/api/v1/materials")
ALLOWED_SUFFIXES = {".md", ".txt"}


def split_content(content: str, max_chars: int = 800) -> Iterator[dict[str, object]]:
    lines = content.splitlines()
    if not lines:
        return

    chunk_index = 0
    index = 0
    while index < len(lines):
        start = index
        parts: list[str] = []
        size = 0
        while index < len(lines):
            line = lines[index]
            addition = len(line) + (1 if parts else 0)
            if parts and size + addition > max_chars:
                break
            if not parts and len(line) > max_chars:
                for offset in range(0, len(line), max_chars):
                    yield {
                        "chunk_index": chunk_index,
                        "content": line[offset : offset + max_chars],
                        "start_line": start + 1,
                        "end_line": start + 1,
                    }
                    chunk_index += 1
                index += 1
                break
            parts.append(line)
            size += addition
            index += 1
        if parts:
            yield {
                "chunk_index": chunk_index,
                "content": "\n".join(parts),
                "start_line": start + 1,
                "end_line": max(start + 1, index),
            }
            chunk_index += 1


@bp.get("")
@auth_required()
def index() -> tuple:
    rows = list_materials(g.user["class_id"])
    return api_response(
        {
            "items": [
                {
                    "id": row["id"],
                    "title": row["title"],
                    "filename": row["filename"],
                    "created_at": row["created_at"],
                }
                for row in rows
            ]
        }
    )


@bp.post("")
@auth_required("teacher")
def upload() -> tuple:
    uploaded = request.files.get("file")
    if uploaded is None or not uploaded.filename:
        raise ApiError(code=1101, message="请选择 Markdown 或 TXT 文件", status=400)

    suffix = Path(uploaded.filename).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise ApiError(code=1102, message="仅支持 Markdown 或 TXT 文件", status=415)

    max_bytes = int(current_app.config["MAX_UPLOAD_BYTES"])
    payload = uploaded.stream.read(max_bytes + 1)
    if len(payload) > max_bytes:
        raise ApiError(code=1103, message="文件超过大小上限", status=413)
    try:
        content = payload.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ApiError(code=1102, message="文件必须使用 UTF-8 编码", status=415) from error
    if not content.strip() or "\x00" in content:
        raise ApiError(code=1101, message="文件内容为空或包含非法字符", status=400)

    requested_title = request.form.get("title", "").strip()
    title = requested_title or Path(uploaded.filename).stem
    if not title or len(title) > 120:
        raise ApiError(code=1101, message="资料标题长度必须为 1 到 120 个字符", status=400)

    chunks = list(split_content(content))
    safe_filename = f"{uuid.uuid4().hex}{suffix}"
    material_id = create_material(
        class_id=g.user["class_id"],
        title=title,
        filename=safe_filename,
        created_by=int(g.user["id"]),
        chunks=chunks,
    )
    return api_response({"id": material_id, "chunks": len(chunks)}, status=201)


@bp.get("/<int:material_id>")
@auth_required()
def detail(material_id: int) -> tuple:
    material = get_material_for_class(material_id, g.user["class_id"])
    if material is None:
        raise not_found()
    chunks = list_chunks(material_id, g.user["class_id"])
    return api_response(
        {
            "material": {
                "id": material["id"],
                "title": material["title"],
                "filename": material["filename"],
                "created_at": material["created_at"],
            },
            "chunks": [
                {
                    "chunk_index": row["chunk_index"],
                    "content": row["content"],
                    "start_line": row["start_line"],
                    "end_line": row["end_line"],
                }
                for row in chunks
            ],
        }
    )
