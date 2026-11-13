from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from scripts.delivery_common import ROOT
from scripts.delivery_runtime import Runtime


def main():
    runtime = Runtime()
    try:
        runtime.start()
        chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True, **({"executable_path": str(chrome)} if chrome.exists() else {})
            )
            context = browser.new_context(
                viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True
            )
            page = context.new_page()
            page.goto(runtime.url)
            page.locator("#username").fill("teacher-a")
            page.locator("#password").fill(runtime.config["SEED_TEACHER_PASSWORD"])
            page.locator("#login").click()
            page.locator("#workspace").wait_for(state="visible")
            page.locator("#title").fill("移动课堂")
            page.locator("#file").set_input_files(
                {
                    "name": "mobile.md",
                    "mimeType": "text/markdown",
                    "buffer": "移动课堂事务隔离".encode(),
                }
            )
            with page.expect_response(
                lambda r: r.url.endswith("/api/v1/materials") and r.request.method == "POST"
            ) as created:
                page.locator("#upload-form button").click()
            assert created.value.status == 201
            material = created.value.json()["data"]["id"]
            page.locator("#query").fill("移动课堂")
            with page.expect_response(lambda r: "/api/v1/search?" in r.url) as search:
                page.locator("#search").click()
            assert search.value.status == 200 and len(search.value.json()["data"]["items"]) == 1
            page.locator("#question").fill("移动课堂事务隔离")
            with page.expect_response(lambda r: r.url.endswith("/api/v1/ask")) as answer:
                page.locator("#ask").click()
            assert answer.value.status == 200
            page.locator("#logout").click()
            page.locator("#auth-card").wait_for(state="visible")
            page.locator("#username").fill("student-b")
            page.locator("#password").fill(runtime.config["SEED_STUDENT_PASSWORD"])
            page.locator("#login").click()
            page.locator("#workspace").wait_for(state="visible")
            results = page.evaluate(
                """async (id)=>{
                const headers={Authorization:'Bearer '+state.token};
                const a=await fetch('/api/v1/materials/'+id,{headers});
                const b=await fetch('/api/v1/materials/999999',{headers});
                return {cross:a.status,missing:b.status,a:await a.text(),b:await b.text()};
            }""",
                material,
            )
            assert results["cross"] == results["missing"] == 404 and results["a"] == results["b"]
            page.screenshot(path=str(ROOT / "reports/lesson10/mobile-viewport.png"), full_page=True)
            teacher = runtime.client("teacher-b")
            status, events = teacher.request("/api/v1/audit-logs")
            assert status == 200
            records = [
                e
                for e in events["data"]["items"]
                if e["actor"] and e["actor"]["username"] == "student-b" and e["result"] == 404
            ]
            assert len(records) >= 2
            (ROOT / "reports/lesson10/mobile.json").write_text(
                json.dumps(
                    {
                        "kind": "automated-mobile-viewport",
                        "real_phone": False,
                        "viewport": [390, 844],
                        "upload": 201,
                        "search": 200,
                        "ask": 200,
                        "cross": 404,
                        "identical_404": True,
                        "audited_denials": records,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            browser.close()
    finally:
        runtime.close()
    print("Automated mobile viewport sync flow and seven-field audit verified.")


if __name__ == "__main__":
    main()
