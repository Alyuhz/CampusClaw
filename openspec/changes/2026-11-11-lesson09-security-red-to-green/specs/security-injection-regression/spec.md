# Spec Delta

## Purpose

为当前班级知识库落实第九课可复测的安全边界和交付证据，让组员能独立重放真实检查，辨别已通过的运行结果、条件不适用与尚需外部执行的事项。

## ADDED Requirements

### Requirement: 可执行三件套
make check SHALL 执行 SQL、真实 DOM XSS 与跨站 CSRF 反例，失败 MUST 非零。

#### Scenario: 可执行三件套复测
- **前置条件**：隔离数据与两个班教师/学生身份，固定场景与提交。
- **WHEN / 操作**：运行注入三件套
- **THEN / 可观测结果**：SQL 不扩大结果，DOM 标题转义且无注入脚本；跨站表单无身份 401、无残留。

### Requirement: 一次性 CSRF
认证写请求 SHALL 携带会话绑定 Cookie 与 10 分钟一次性令牌；Cookie MUST HttpOnly/SameSite=Strict，生产 Secure。

#### Scenario: 一次性 CSRF复测
- **前置条件**：隔离数据与两个班教师/学生身份，固定场景与提交。
- **WHEN / 操作**：合法写、缺失/重放/过期/错绑定与并发消费
- **THEN / 可观测结果**：合法写成功；无身份 401，CSRF 失败 403；同令牌至多成功一次，不绕过身份与角色。
