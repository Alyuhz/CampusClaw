"""Lesson 9 three-part regression cases; see adjacent scenario records."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

import pytest
from flask import Flask
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

from campusclaw import db
from tests.test_api import upload_material


@pytest.fixture()
def live_app(app):
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    thread.join()


@pytest.fixture()
def browser():
    with sync_playwright() as playwright:
        chrome = os.environ.get(
            "CHROME_EXECUTABLE", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        )
        options = {"executable_path": chrome} if Path(chrome).exists() else {}
        browser = playwright.chromium.launch(headless=True, **options)
        yield browser
        browser.close()


def test_sql_injection_no_extra_rows(client, login):
    # Given isolated A/B data; When injecting an SQL predicate; Then no rows leak.
    a = login("teacher-a")
    assert upload_material(client, a, "SQL课程", "数据库事务隔离唯一知识").status_code == 201
    b = login("teacher-b")
    assert upload_material(client, b, "B课程", "其他班级独有材料").status_code == 201
    for identity in ["student-a", "student-b"]:
        headers = login(identity)
        response = client.get("/api/v1/search", query_string={"q": "' OR '1'='1"}, headers=headers)
        assert response.status_code == 200
        assert response.get_json()["data"]["items"] == []


def test_xss_actual_dom_source(browser, live_app):
    # Given a malicious title; When rendering the real list; Then the DOM escapes it.
    page = browser.new_page()
    page.goto(live_app)
    page.locator("#username").fill("teacher-a")
    page.locator("#password").fill("teacher-pass")
    page.locator("#login").click()
    page.locator("#workspace").wait_for(state="visible")
    page.locator("#title").fill("<script>alert(1)</script>")
    page.locator("#file").set_input_files(
        {"name": "course.md", "mimeType": "text/markdown", "buffer": "事务隔离资料".encode()}
    )
    with page.expect_response(
        lambda r: r.url.endswith("/api/v1/materials") and r.request.method == "POST"
    ) as response:
        page.locator("#upload-form button").click()
    assert response.value.status == 201
    li = page.locator("#materials li")
    li.wait_for()
    html = li.evaluate("(node)=>node.outerHTML")
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert li.locator("script").count() == 0
    assert li.evaluate('(n)=>Array.from(n.attributes).every(a=>!a.name.startsWith("on"))')
    evidence = os.environ.get("CAMPUSCLAW_EVIDENCE_DIR")
    if evidence:
        Path(evidence, "xss-dom.html").write_text(html + "\n")
    page.close()


def test_csrf_replay_and_production_cookie(app, client, login):
    # Given a valid teacher session; When token is missing/replayed; Then reject.
    app.config["COOKIE_SECURE"] = True
    response = client.post(
        "/api/v1/auth/login", json={"username": "teacher-a", "password": "teacher-pass"}
    )
    cookie = response.headers["Set-Cookie"]
    assert all(attr in cookie for attr in ["HttpOnly", "SameSite=Strict", "Secure"])
    headers = {"Authorization": "Bearer " + response.get_json()["data"]["token"]}
    assert client.post("/api/v1/ask", headers=headers, json={"question": "test"}).status_code == 403
    headers["X-CSRF-Token"] = response.get_json()["data"]["csrf_token"]
    assert client.post("/api/v1/ask", headers=headers, json={"question": "test"}).status_code == 200
    assert client.post("/api/v1/ask", headers=headers, json={"question": "test"}).status_code == 403


def test_csrf_cross_site_form(browser, live_app, app):
    # Given a logged in browser; When another site submits; Then server returns 401.
    evil = Flask("evil")

    @evil.get("/")
    def attack():
        return (
            '<form id="attack" action="'
            + live_app
            + '/api/v1/materials" method="post"><input name="title" value="evil"></form>'
        )

    server = make_server("127.0.0.1", 0, evil, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    page = browser.new_page()
    try:
        page.goto(live_app)
        page.locator("#username").fill("teacher-a")
        page.locator("#password").fill("teacher-pass")
        page.locator("#login").click()
        page.locator("#workspace").wait_for(state="visible")
        page.goto(f"http://localhost:{server.server_port}/")
        with page.expect_response(
            lambda r: r.url.endswith("/api/v1/materials") and r.request.method == "POST"
        ) as response:
            page.locator("#attack").evaluate("(f)=>f.submit()")
        assert response.value.status == 401
        with app.app_context():
            assert db.list_materials("class-a") == []
        evidence = os.environ.get("CAMPUSCLAW_EVIDENCE_DIR")
        if evidence:
            Path(evidence, "csrf-cross-site.json").write_text(
                json.dumps({"http_status": 401, "materials": 0, "cross_site": True}) + "\n"
            )
    finally:
        page.close()
        server.shutdown()
        thread.join()
