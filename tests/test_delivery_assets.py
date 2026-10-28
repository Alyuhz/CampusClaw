from pathlib import Path


def test_ui_declares_four_states_and_disables_pending_actions():
    html = Path("campusclaw/templates/index.html").read_text(encoding="utf-8")
    script = Path("campusclaw/static/app.js").read_text(encoding="utf-8")

    for element_id in ("materials-status", "search-status", "upload-status", "answer"):
        assert f'id="{element_id}"' in html
    assert "正在加载资料…" in script
    assert "本班暂无资料" in script
    assert "资料中未找到相关内容" in script
    assert "setBusy(button, true)" in script
    assert "button.disabled = busy" in script
    assert "innerHTML" not in script


def test_write_endpoints_have_explicit_idempotency_contract():
    api_docs = Path("docs/api.md").read_text(encoding="utf-8")

    for path, semantics in (
        ("/api/v1/auth/login", "非幂等"),
        ("/api/v1/auth/logout", "副作用幂等"),
        ("/api/v1/materials", "非幂等"),
        ("/api/v1/ask", "非幂等"),
    ):
        assert path in api_docs
        assert semantics in api_docs
    assert "Idempotency-Key" in api_docs


def test_container_command_uses_valid_gunicorn_factory_syntax():
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")

    assert "--factory" not in dockerfile
    assert "campusclaw:create_app()" in dockerfile
    assert '--config", "gunicorn.conf.py"' in dockerfile
