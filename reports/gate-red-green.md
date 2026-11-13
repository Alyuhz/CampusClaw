# 安全门禁红绿证据

实际入口：`make check-security`，依次执行密钥扫描和两份依赖锁审计；任一失败返回非零，CI 也执行。漏洞库不可达、工具错误、过期或错配例外同样阻断。

本次红绿在隔离临时 Git 仓库执行相同真实门禁路径，只放合成风险，不用真实密钥；处理方式为移除临时风险文件。它证明门禁有效，不能冒充真实泄露轮换。

| 项目 | 红运行 | 绿运行 |
|---|---|---|
| 命令 | make check-security SECURITY_ROOT=<isolated-fixture> | 相同命令 |
| 实际退出码 | 2 | 0 |
| 密钥扫描 | 命中合成文件，失败 | 无命中，通过 |
| 依赖审计 | 最终锁文件，无未处置风险 | 同上 |
| 输出 | [gate-red.txt](evidence/gate-red.txt) | [gate-green.txt](evidence/gate-green.txt) |

被测基线：`e42b90293e1f3c0eb57dd26f127274801048e5e3`；工作区摘要：`0c07e9d4a9327d1e77b5345d5619ca176eec8dfbcb768cba88f9fb7817c0aa01`；夹具提交：`06d6309a683f156433b6fe80d781070a4ae86750`。所有业务修改未提交。
工具版本：Python 3.12.16、pip-audit 2.10.1；执行日期 2026-11-11。机器记录：[gate-red-green.json](evidence/gate-red-green.json)。业务真实门禁另见 [check-security-final.txt](evidence/check-security-final.txt)，退出 0。

依赖前后真实报告另归档，不与合成风险红绿混用。无真实泄露命中，没有执行轮换或改写共享仓库历史。

## 第十课隔离坏断言实验

手段：`python -m scripts.gate_red_green`，复制工作树与只读来源的Git历史到临时目录；只在副本把健康测试期望200改为299，运行同一条`make check`，恢复原文后再跑。主工作区测试不改坏。

四件证据：[坏断言diff](lesson10/gate/mutation.diff)、[红屏](lesson10/gate/red.txt)、[红绿退出码和版本](lesson10/gate/result.json)、[绿屏](lesson10/gate/green.txt)。红退出2，恢复后绿0。该脚本可复跑。

本地没有创建修复提交；版本用基线完整SHA与源文件摘要定位，真实修复提交编号待维护者提交后补齐，不能冒充提交证据。本课保留上方第九课记录，最终门禁见 [本课核验](lesson10/final-verification.json)。
