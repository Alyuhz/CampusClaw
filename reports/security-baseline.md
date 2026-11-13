# 第 9 课安全基线

- 检查时间：2026-11-11T08:39:33+08:00
- 被测提交：`e42b90293e1f3c0eb57dd26f127274801048e5e3`
- 环境：macOS；系统 `python3` 为 Python 3.14.4；`uv` 位于 `/opt/homebrew/bin/uv`。
- 项目要求：Python 3.12，依赖由 `requirements-dev.lock` 固定。
- 工作区：已有未提交 OpenSpec 提案与 `openspec/config.yaml`；本次未修改业务代码。

## 功能检查首次实际

命令：`make check`

退出码：`2`

完整输出：

```text
.venv/bin/python -m ruff check .
make: .venv/bin/python: No such file or directory
make: *** [lint] Error 1
```

判定：环境阻塞。项目虚拟环境不存在，检查未进入 Ruff、编译、测试、分层、密钥扫描和规约验证，不能判定业务用例通过或失败。历史文档的 19 passed 不作为本次结果。

## 最初检查状态（历史记录）

SEC-01～08 尚未运行本次动态重放，没有新的安全绿项证据。资产扫描、依赖审计、镜像检查及真实模型实验均未执行。后续已修复环境并运行同一命令，结果见下；SEC 全量专项重放仍未执行。

## 环境修复后复测

日期：2026-11-11。被测业务提交仍为 `e42b90293e1f3c0eb57dd26f127274801048e5e3`，工作区仅有规划和报告变更。
本机解释器 `/opt/homebrew/bin/python3.12` 为 Python 3.12.16；使用其创建 `.venv`，由官方 PyPI 安装原 `requirements-dev.lock` 中的 16 个包。没有下载 Python，没有修改锁文件。

命令：`make check`。退出码：`0`。完整输出：

```text
.venv/bin/python -m ruff check .
All checks passed!
.venv/bin/python -m ruff format --check .
17 files already formatted
.venv/bin/python -m compileall -q campusclaw tests scripts
.venv/bin/python -m pytest
...................                                                      [100%]
19 passed in 2.63s
.venv/bin/python scripts/check_layout.py
layout: ok
.venv/bin/python scripts/secret_scan.py
secret-scan: ok
.venv/bin/python scripts/validate_change.py
spec-check: ok (1 archived change)
```

判定：现有功能门禁通过。首次缺环境属于检查环境故障，不是安全漏洞红项，也不是 `make check-security` 的红绿证据。

## 文档阶段资产状态（历史记录，最终结果见下）

| 项目 | 实际 | 判定 |
|---|---|---|
| 现有密钥扫描 | `scripts/secret_scan.py` 输出 secret-scan: ok | 在脚本当前匹配规则范围内通过 |
| 工作树范围 | Git 跟踪及未忽略文件中的指定文本类型 | 不含被忽略的个人 .env；不能推断所有文件均扫描 |
| 历史范围 | `git log -p --all` | 仅当前本地可见引用历史，不代表远端所有历史 |
| 匹配规则 | 私钥头、部分常见令牌格式、示例/历史部分敏感配置 | 不是通用泄露证明，未知格式仍可能漏检 |
| 模型凭证落库 | 现有迁移无模型凭证字段；users 保存 password_hash | 可解密模型密钥加密存储场景不适用；密码哈希不是模型密钥 |
| 依赖漏洞审计 | 未运行 | 待验证，不能填写高危 0 |
| 镜像最终层和历史层 | 未构建、未扫描 | 待验证 |
| 真实密钥轮换/失效验证 | 未执行，本次扫描未报告命中 | 不得编造旧值 401 |
| 安全聚合门禁 | Makefile 没有 check-security | 缺口，见 gate-red-green.md |

## 后续资产核查流程（操作说明，未执行）

1. 密钥扫描发现真实命中时，仅记录路径/字段/提交号，不抄值；立即由持有人在服务商轮换。
2. 由持有人用旧值验证失效，记录时间、服务与实际响应状态，课程预期为 401；不把值或认证头写报告。
3. 协调全组暂停写入，另行确认历史清理方案；清理后重扫并通知重新克隆。不能只删除当前文件当作修复。
4. 依赖审计覆盖运行/开发锁文件，记录工具版本、日期、漏洞库、命令、退出码及原始脱敏报告；不可达不算通过。
5. 漏洞登记字段：包名、受影响版本、漏洞编号、严重级别、暂不修理由、缓解措施、责任人、到期日、复核证据。登记不等于实际零漏洞。
6. 镜像检查记录镜像摘要与层摘要，检查最终文件系统和各历史层的秘密、.env、凭证及构建上下文；未构建保持待验证。

记录模板：检查项｜被测提交/镜像摘要｜命令与版本｜检查时间｜退出码｜脱敏证据路径｜实际发现｜责任人｜下一步。

## 完整安全实现后的最终基线

日期：2026-11-11。源码提交：`e42b902 + 工作区摘要`。依赖仅从官方 PyPI 获取，Python 使用本机 3.12.16，浏览器复用本机 Chrome。

- `make check`：退出 0，51 passed in 9.61s；[完整输出](evidence/make-check-final.txt)。
- 注入专项：4 个用例通过，覆盖 SQL、实际 DOM、CSRF 双开关与跨站表单；[输出](evidence/injection-final.txt)。
- `make check-security`：退出 0；secret-scan: ok；dependency-audit: ok, unhandled=0, exceptions=0；[输出](evidence/check-security-final.txt)。
- 原依赖审计：4 个包共 28 条报告项（含重复漏洞编号）；[原始 JSON](evidence/dependencies-before.json)。
- 最终运行与开发锁审计：无已知漏洞、无例外；[最终 JSON](evidence/dependencies-current.json)。所有已知未登记漏洞均阻断，严于仅阻断高危。

| 包 | 原版本 | 修复版本 |
|---|---|---|
| Flask | 3.1.2 | 3.1.3 |
| PyJWT | 2.10.1 | 2.15.1 |
| python-dotenv | 1.1.1 | 1.2.4 |
| pytest | 8.4.2 | 9.2.0 |

并同步更新传递依赖与开发工具锁文件。针对原 PyJWT 弱密钥争议报告，应用另要求 JWT_SECRET_KEY 至少 32 字节，不依赖库升级代替配置约束。

密钥扫描修复了历史 diff 的 +/- 前缀导致环境键值漏检；删除历史夹具验证为非零且不回显值。真实仓库当前规则内零命中，无真实泄露轮换条件触发。没有执行真实旧密钥请求或历史重写，不把无命中记成“轮换通过”。扫描局限仍为脚本所列格式和本地可见引用。

镜像已构建、健康通过、UID 10001，10 层扫描未命中；[实际范围与摘要](evidence/docker-verification.json)。所有层的文本文件按说明扫描；二进制、压缩内容与未知格式不宣称穷尽检查。构建口令没有写入镜像，运行使用临时随机值，容器和临时文件已清理。

SQLite 备份/恢复、重复迁移和双线程首次迁移验证通过；新迁移只增两表，旧业务与审计数据恢复后保持。测试从不读开发数据库或调用真实模型。

真实模型实验因本项目没有本地 .env 与进程 GLM_API_KEY 未执行；未读取其他项目的凭证。四步恶意替身证据另见 sec08-experiment.md，不冒充真实模型。
