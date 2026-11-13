# 首次记录（保留基线）

# INJ-XSS-01：资料标题输出转义

状态：文档已编写，浏览器专项未执行；不是自动回归用例。

- **前置条件**：临时数据库与教师 A；上传合法 Markdown，标题精确为 `<script>alert(1)</script>`。
- **操作**：登录页面加载资料列表，检查浏览器 Elements 中对应 li 的 outerHTML（实际 DOM 序列化源码）；同时查看 static/app.js 中列表和问答节点的赋值方式。保存该节点源码与 DOM 元素检查结果。原始 View Source 只有页面壳，不能代替动态列表检查。
- **可观测结果**：期望标题作为文本显示，outerHTML 中为 `&lt;script&gt;alert(1)&lt;/script&gt;`，标题未生成 script 节点或事件属性。问答引用标题也仅为文本。看是否弹窗不能作为判据。

## 当前实际与证据

首次实际：源码 loadMaterials 使用 li.textContent，搜索与问答使用 textContent；浏览器动态 DOM 未检查。
当前实际：待验证。所需证据：上传 201 响应、实际节点源码、节点/事件属性核对、提交号、时间与操作者；不保存令牌或用户资料正文。
判定：源码存在安全赋值路径，专项运行仍待验证。页面原本引用的合法脚本不能误判为标题注入。


# 修复后复测：2026-11-11

当前状态：已执行并通过，已由 test_injection.py 接入 make check；原“尚未执行/未接入”文字属于首次记录。

- **前置条件**：同原记录，使用临时数据库与本机 Chrome。
- **操作**：重放固定场景 test_xss_actual_dom_source。
- **可观测结果**：教师上传 201；真实页面 li.outerHTML 包含 &lt;script&gt;，注入 script 节点为 0，未生成事件属性。源码见 reports/evidence/xss-dom.html。

证据：reports/evidence/injection-final.txt、make-check-final.txt。CSRF 机制是本轮明确授权后新增，与首次 Bearer-only 架构区别记录，不把无认证 Cookie 算作 SameSite 通过。
