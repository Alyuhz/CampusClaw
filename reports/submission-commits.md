# 本地提交索引

2026-11-13，经确认将已有真实修复快照整理为分项本地提交；没有推送，也没有修改远端设置。各提交树在临时目录独立通过make check，实际创建时使用现有提交钩子。

| 条目 | 完整提交号 | 内容 |
|---|---|---|
| SEC-01 | `a67ef80b3062daf9078c3d037e979c9b2efe2783` | fix: SEC-01 default-deny protected API authentication |
| SEC-02 | `55eeb559437732f473e958fd286b8cdc194df7c0` | fix: SEC-02 enforce material class ownership |
| SEC-04 | `3e11832ae4ad480ac8af6154ba7d9b43af4a2969` | fix: SEC-04 authorize transactional writes by session role and ownership |
| SEC-07 | `2bc56ca30bb25ce56748c7ab4bccb68df5463030` | fix: SEC-07 persist audit outcomes including denied requests |
| injection | `140968ebb5bed68229012ee680e39fc021851d44` | fix: add single-use CSRF and SQL XSS injection regressions |
| SEC-08 | `dbeeedb7cf954881af8333b700b1e8b987c5adc1` | test: SEC-08 verify adversarial model tool authorization boundaries |
| SEC-05 | `d9d603797de226bbc911f6a63237d92bfdd3d202` | fix: SEC-05 scan secret history and verify credential-free image layers |
| SEC-06 | `9ab8d3cd5a696ebeb23cc1a2e79fe88f54984c95` | fix: SEC-06 upgrade vulnerable dependencies and enforce security audit gate |

SEC-03教师角色检查在基线已存在，本课补复测，不另称修复提交；SQL/XSS已有实现补反例，CSRF新增一次性令牌。SEC-08为恶意替身实验，真实模型与人工项目仍待外部条件。

[逐提交检查结果](submission/split-validation.json) 与同目录完整输出。第十课交付实现与第九课文档/证据由本索引所在的交付提交保存，后续核验补记记录其实际编号。

历史报告中的“未提交”、基线SHA、工作区摘要及原始输出均为当时验证状态，不改写成当时已有提交。新提交编号与历史验证来源分别记录；本地提交不代表GitHub推送、CI、主干保护或人工验收已完成。

## 第十课实现与最终核验

交付实现提交：`44a83af6439e8e1de9436be7f4197b921f2ca264`。该提交包含检索缓存改进、就绪/指标修复、容器与CI配置、观测和交付证据。

对该实际提交运行双门禁：[记录](submission/committed-verification.json)、[全量85通过](submission/check.txt)、[安全32通过](submission/security.txt)。本索引的后续文档提交只补真实编号和原始结果，不改业务代码。

## 远端推送补记

2026-11-13，SSH认证成功，已将开发分支codex/lesson09-security推送到Alyuhz/CampusClaw；远端逐字核对提交为`c016365f474b4afecd866ccc3d35aa5f12601a4d`。本节后续文档补记也随同分支上传，不合并main。前文“未推送”为此前状态。

[实际推送与CI记录](submission/push-verification.json)：GitHub运行43367998192在任何步骤启动前失败，提示账号因账单问题被锁；不是测试断言失败，也不能计CI或镜像构建通过。需仓库所有者处理账号运行条件。外部验收7.4仍待CI构建与主干保护证据。
