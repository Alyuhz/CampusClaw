from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from pathlib import Path

from flask import Blueprint, current_app, g, request

from .auth import auth_required
from .http import ApiError, api_response
from .search import search

bp = Blueprint("assistant", __name__, url_prefix="/api/v1")
PROMPT_PATH = Path(__file__).with_name("prompts") / "answer.md"


def _extractive_answer(citations: list[dict[str, object]]) -> str:
    lines = []
    for number, citation in enumerate(citations, start=1):
        lines.append(f"{citation['snippet']} [{number}]")
    return "根据本班资料：\n" + "\n".join(lines)


def _glm_answer(question: str, citations: list[dict[str, object]]) -> str:
    evidence = "\n\n".join(
        f"[{index}] 资料：{item['title']}，第 {item['start_line']}-{item['end_line']} 行\n"
        f"{item['snippet']}"
        for index, item in enumerate(citations, start=1)
    )
    payload = {
        "model": current_app.config["GLM_MODEL"],
        "temperature": current_app.config["GLM_TEMPERATURE"],
        "messages": [
            {
                "role": "system",
                "content": PROMPT_PATH.read_text(encoding="utf-8"),
            },
            {
                "role": "user",
                "content": f"问题：{question}\n\n课程资料：\n{evidence}",
            },
        ],
    }
    request_object = urllib.request.Request(
        "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers={
            "Authorization": f"Bearer {current_app.config['GLM_API_KEY']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(
            request_object,
            timeout=int(current_app.config["GLM_TIMEOUT_SECONDS"]),
        ) as response:
            body = json.load(response)
        answer = body["choices"][0]["message"]["content"]
    except (KeyError, TypeError, ValueError, urllib.error.URLError) as error:
        raise ApiError(code=1500, message="模型服务暂不可用", status=503) from error
    if not isinstance(answer, str) or not answer.strip():
        raise ApiError(code=1500, message="模型服务暂不可用", status=503)
    answer = answer.strip()
    references = [int(number) for number in re.findall(r"\[(\d+)\]", answer)]
    if not references or any(number < 1 or number > len(citations) for number in references):
        raise ApiError(code=1500, message="模型输出缺少有效引用", status=503)
    return answer


@bp.post("/ask")
@auth_required()
def ask() -> tuple:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ApiError(code=1101, message="请求体必须是 JSON 对象", status=400)
    question = payload.get("question")
    if not isinstance(question, str) or not question.strip() or len(question.strip()) > 300:
        raise ApiError(code=1101, message="问题长度必须为 1 到 300 个字符", status=400)

    citations = search(
        g.user["class_id"],
        question.strip(),
        int(current_app.config["SEARCH_RESULT_LIMIT"]),
    )
    if not citations:
        return api_response(
            {
                "answer": "资料中未找到相关内容",
                "citations": [],
                "degraded": False,
            }
        )

    if current_app.config.get("GLM_API_KEY"):
        answer = _glm_answer(question.strip(), citations)
        degraded = False
    else:
        answer = _extractive_answer(citations)
        degraded = True
    return api_response(
        {
            "answer": answer,
            "citations": citations,
            "degraded": degraded,
        }
    )
