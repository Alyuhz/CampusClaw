from __future__ import annotations

import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import UTC, datetime

from scripts.delivery_common import ROOT

MAPPING = {
    "合法账号登录": ["tests/test_api.py::test_search_and_ask_only_use_current_class"],
    "登录失败不泄露账号是否存在": [
        "tests/test_api.py::test_login_failures_do_not_reveal_existing_account"
    ],
    "教师上传 Markdown 资料": ["tests/test_api.py::test_only_teachers_can_upload"],
    "学生调用教师上传接口": ["tests/test_security.py::test_sec03_no_residual_data"],
    "读取跨班或不存在的资料": [
        "tests/test_api.py::test_cross_class_and_missing_material_have_identical_404_bodies"
    ],
    "仅检索本班资料": ["tests/test_security.py::test_sec02_both_search_paths"],
    "问题带真实出处回答": ["tests/test_api.py::test_search_and_ask_only_use_current_class"],
    "无依据问题不编造出处": [
        "tests/test_api.py::test_ask_without_evidence_never_invents_a_citation"
    ],
    "客户端伪造班级参数": ["tests/test_api.py::test_class_id_from_query_is_ignored"],
    "健康检查免认证": ["tests/test_api.py::test_health_is_public_and_structured"],
    "默认认证与角色复测": ["tests/test_security.py::test_sec01_matrix"],
    "逐资源与底层授权复测": [
        "tests/test_security.py::test_sec04_direct_session_roles_and_ownership",
        "tests/test_security.py::test_sec02_both_search_paths",
    ],
    "资产与密钥历史复测": [
        "tests/test_security_gate.py::test_secret_in_deleted_history_is_detected_without_echo"
    ],
    "依赖审计与门禁复测": ["tests/test_security_gate.py::test_dependency_tool_failure_blocks"],
    "七列持久日志复测": ["tests/test_security.py::test_audit_class_filter_and_validation"],
    "实验与真实证据复测": ["tests/test_sec08.py::test_sec08_adversarial_model_execution_boundary"],
    "可执行三件套复测": [
        "apitest/cases/test_injection.py::test_sql_injection_no_extra_rows",
        "apitest/cases/test_injection.py::test_xss_actual_dom_source",
    ],
    "一次性 CSRF复测": ["apitest/cases/test_injection.py::test_csrf_replay_and_production_cookie"],
    "逐场景定位用例": ["tests/test_delivery_quality.py::test_traceability_nodes_are_collectable"],
    "故意坏断言被拦": ["tests/test_delivery_quality.py::test_actual_bad_assertion_red_green"],
    "安全门禁失败阻断": [
        "tests/test_delivery_quality.py::test_ci_gates_precede_build",
        "tests/test_security_gate.py::test_dependency_tool_failure_blocks",
    ],
    "本地与远端证据区分": [
        "tests/test_delivery_transport.py::test_build_refuses_false_clean_revision"
    ],
    "换目录启动": ["tests/test_delivery_quality.py::test_actual_clean_runtime"],
    "数据库故障": ["tests/test_delivery.py::test_ready_readonly_and_database_failure"],
    "扫描并启动打包产物": ["tests/test_delivery_quality.py::test_actual_clean_runtime"],
    "多进程精确计数": [
        "tests/test_delivery_quality.py::test_actual_workers_and_restart",
        "tests/test_delivery.py::test_metrics_concurrent_exact_and_duplicate",
    ],
    "生成真实流量": ["tests/test_delivery_quality.py::test_actual_dashboard_queries"],
    "持续错误触发": ["tests/test_delivery_quality.py::test_actual_alert_delivery_and_recovery"],
    "两轮数据对齐": ["tests/test_delivery_quality.py::test_benchmark_matching_protocol"],
    "缓存不越权且及时失效": [
        "tests/test_delivery.py::test_cache_class_write_invalidation_and_revocation"
    ],
    "检验缓存收益": ["tests/test_delivery_quality.py::test_benchmark_actual_benefit"],
    "移动端同步验收": ["tests/test_delivery_quality.py::test_actual_mobile_viewport"],
    "复核证据完整": ["tests/test_delivery_quality.py::test_review_and_risk_records"],
    "独立打开最终材料": ["tests/test_delivery_quality.py::test_report_links_resolve"],
}


def build():
    run = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-o", "addopts="],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    collected = {
        line.strip()
        for line in run.stdout.splitlines()
        if "::" in line and not line.startswith(" ")
    }
    entries = []
    folders = [
        ROOT / "openspec/changes/archive/2026-10-28-class-material-search",
        ROOT / "openspec/changes/2026-11-11-lesson09-security-red-to-green",
        ROOT / "openspec/changes/2026-11-11-lesson10-delivery-validation",
    ]
    for folder in folders:
        for path in sorted((folder / "specs").glob("*/spec.md")):
            for title in re.findall(
                r"^(?:#### Scenario: |### 场景：)(.+)$", path.read_text(), re.M
            ):
                nodes = MAPPING.get(title, [])
                expanded = [
                    node
                    for prefix in nodes
                    for node in sorted(collected)
                    if node == prefix or node.startswith(prefix + "[")
                ]
                if not expanded:
                    raise ValueError(f"Uncovered automated scenario: {title}")
                entries.append(
                    {
                        "scenario_id": f"SC-{len(entries) + 1:03d}",
                        "source": str(path.relative_to(ROOT)),
                        "scenario": title,
                        "nodeids": expanded,
                        "command": "make check",
                        "coverage": "collectable-test plus actual script evidence where noted",
                    }
                )
    return entries


def main():
    entries = build()
    xml = ROOT / "reports/lesson10/pytest.xml"
    executed = {}
    if xml.exists():
        suite = ET.parse(xml).getroot()
        for case in suite.iter("testcase"):
            node = case.attrib["classname"].replace(".", "/") + ".py::" + case.attrib["name"]
            status = "passed"
            for flag in ("failure", "error", "skipped"):
                if case.find(flag) is not None:
                    status = flag
            executed[node] = status
        recorded = datetime.fromtimestamp(xml.stat().st_mtime, UTC).isoformat()
        for entry in entries:
            entry["last_execution"] = {
                "time": recorded,
                "results": {
                    node: executed.get(node, "not in latest run") for node in entry["nodeids"]
                },
                "evidence": "reports/lesson10/pytest.xml",
            }
    output = ROOT / "reports/lesson10/traceability.json"
    output.write_text(
        json.dumps(
            {
                "generated": datetime.now(UTC).isoformat(),
                "uncovered_automated": 0,
                "scenarios": entries,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    lines = [
        "# 场景可追溯矩阵",
        "",
        "覆盖含义：可收集测试与实际脚本证据分别记录；文件映射不等于实机/三人/远端已通过。"
        "最后运行结果见 lesson10 最终门禁记录。",
        "",
        "| 场景ID/来源 | 场景 | 可收集用例 | 命令 | 最近实际结果 |",
        "|---|---|---|---|---|",
    ]
    for entry in entries:
        lines.append(
            "| "
            + entry["scenario_id"]
            + " / "
            + entry["source"]
            + " | "
            + entry["scenario"]
            + " | "
            + "<br>".join(entry["nodeids"])
            + " | make check | "
            + str(entry.get("last_execution", {}).get("results", "未读取执行记录"))
            + " / "
            + entry.get("last_execution", {}).get("time", "尚无时间")
            + " |"
        )
    lines += [
        "",
        "自动化适用场景未覆盖数：0。",
        (
            "最近结果来源：[实际JUnit](lesson10/pytest.xml)，时间取该实际执行文件更新时间；未在最近运行中出现则明确标记。"
            if xml.exists()
            else "首次实际JUnit尚未生成，执行make check后再生成此矩阵。"
        ),
        "",
        "## 外部部分不计机器通过",
        "",
        "移动端场景的真实手机/三人反馈、人工交叉评审、真实GitHub构建与主干保护、"
        "外部负责人通知、原版技能/异步/数据库适配，分别对应 tasks.md 第7组，保持待真实执行。"
        "测试仅验证本地自动化部分及证据完整性，不代签外部结果。",
    ]
    (ROOT / "reports/traceability.md").write_text("\n".join(lines) + "\n")
    print(f"{len(entries)} scenarios mapped to collectable test nodes.")


if __name__ == "__main__":
    main()
