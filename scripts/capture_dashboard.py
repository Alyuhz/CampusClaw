from __future__ import annotations

import json
import subprocess
from pathlib import Path

from playwright.sync_api import sync_playwright

from scripts.delivery_common import ROOT


def main():
    ids = subprocess.check_output(
        [
            "docker",
            "ps",
            "-q",
            "--filter",
            "name=cc10-",
            "--filter",
            "label=com.docker.compose.service=grafana",
        ],
        text=True,
    ).split()
    if len(ids) != 1:
        raise RuntimeError("Expected one isolated lesson10 Grafana")
    info = json.loads(subprocess.check_output(["docker", "inspect", ids[0]], text=True))[0]
    folder = Path(info["Config"]["Labels"]["com.docker.compose.project.working_dir"])
    if not folder.name.startswith("campusclaw-delivery-"):
        raise RuntimeError("Not a lesson10 temporary runtime")
    values = dict(line.split("=", 1) for line in (folder / ".env").read_text().splitlines())
    url = "http://127.0.0.1:" + values["GRAFANA_PORT"]
    chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True, **({"executable_path": str(chrome)} if chrome.exists() else {})
        )
        context = browser.new_context(viewport={"width": 1440, "height": 1100})
        response = context.request.post(
            url + "/login", data={"user": "admin", "password": values["GRAFANA_ADMIN_PASSWORD"]}
        )
        assert response.status == 200
        page = context.new_page()
        page.goto(url + "/d/campusclaw/capabilities?orgId=1&from=now-15m&to=now")
        page.get_by_text("Calls by capability", exact=True).wait_for(timeout=60000)
        page.wait_for_timeout(5000)
        page.screenshot(path=str(ROOT / "reports/lesson10/grafana-dashboard.png"), full_page=True)
        data = context.request.get(url + "/api/dashboards/uid/campusclaw").json()
        assert len(data["dashboard"]["panels"]) == 4
        (ROOT / "reports/lesson10/dashboard-provisioned.json").write_text(
            json.dumps(data["dashboard"], indent=2)
        )
        browser.close()
    print("Real provisioned Grafana dashboard captured.")


if __name__ == "__main__":
    main()
