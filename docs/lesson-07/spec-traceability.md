# 第 7 课能力与 Scenario 追踪

## 能力与场景

| 能力 | Scenario | 验证 |
|---|---|---|
| 外部配置 | 缺少必填配置时拒绝启动 | `tests/test_config.py::test_each_required_configuration_fails_fast` |
| 外部配置 | 示例配置不包含值 | `tests/test_config.py::test_env_example_contains_only_blank_values` |
| 单行 JSON 日志 | 健康检查产生结构化日志 | `tests/test_api.py::test_request_log_is_one_json_line_with_matching_request_id` |
| 四种状态 | 检索无结果 | `tests/test_delivery_assets.py::test_ui_declares_four_states_and_disables_pending_actions` |
| 四种状态 | 请求进行中阻止重复操作 | 同上，并检查 `setBusy` 与 `button.disabled` |
| 写接口幂等 | 重复上传的语义可查询 | `tests/test_delivery_assets.py::test_write_endpoints_have_explicit_idempotency_contract` |
| 失败路径 | 参数非法 | `tests/test_api.py::test_search_rejects_invalid_query_and_limit_without_full_scan` |
| 失败路径 | 无权限 | `tests/test_api.py::test_only_teachers_can_upload` |
| 失败路径 | 资源不存在或跨班 | `tests/test_api.py::test_cross_class_and_missing_material_have_identical_404_bodies` |
| 失败路径 | 依赖不可达 | `tests/test_api.py::test_model_dependency_failure_is_explicit` |
| 健康依赖状态 | 数据库不可用 | `tests/test_api.py::test_health_reports_database_dependency_failure` |
| 容器入口 | Gunicorn factory 语法 | `tests/test_delivery_assets.py::test_container_command_uses_valid_gunicorn_factory_syntax` |

## 历史归档补数

历史 `class-material-search` 的场景保持不变。本变更补充了依赖不可达 Scenario，并在同一
能力追踪表中给出可执行测试。没有改写归档历史。
