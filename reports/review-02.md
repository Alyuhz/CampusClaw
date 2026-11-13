# 评审 02：脚本与门禁输出

- **手段**：本机 Python 3.12.16 运行 make check、注入专项、make check-security；本机 Chrome、Docker 实测。
- **查了什么**：51 个回归（授权、双检索、残留、CSRF、真实 DOM/跨站、审计、门禁本身、备份与并发迁移、恶意模型替身），依赖、密钥历史和镜像。
- **判据**：功能/安全命令退出 0；安全合成风险实验先非零后零；镜像 health=ok、uid 非零、已声明扫描范围无命中；不跳过用例、不替换预期。
- **结果**：全部本地命令通过，实际输出见 evidence/make-check-final.txt、injection-final.txt、check-security-final.txt、gate-red-green.json、docker-verification.json。

真实模型与独立组员评审未执行；不存在模块不纳入“绿”。本地修改未提交、未推送，版本由基线与 source-manifest.json 标识。
