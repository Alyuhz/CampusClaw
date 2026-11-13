# 首次记录（保留基线）

# INJ-CSRF-01：跨站请求与防护差异

状态：文档已编写，跨站浏览器实验未执行；不是自动回归用例。

## 当前认证事实

auth.py 读取 Authorization: Bearer；前端 app.js 将 token 保存在内存。登录不设置认证 Cookie；没有一次性 CSRF 令牌。不能把“没有认证 Cookie”写成“Cookie 已设置 SameSite”，也不能因为缺少 CSRF 令牌仍能正常 Bearer 上传就断言远程跨站攻击成功。

## A：跨站请求

- **前置条件**：教师在应用页面登录；另一个独立站点页面不持有其 Bearer。使用临时数据库，记录资料数量。
- **操作**：从另站点用普通表单向真实教师上传接口 POST /api/v1/materials 提交合法字段和文件；检查 Network 响应与数据库变化，不主动给攻击页添加合法 Bearer。
- **可观测结果**：期望缺少身份被拒为 401，业务无新增；记录实际跨站导航与提交，不以 CORS 报错独自替代服务端拒绝证据。
- 首次实际/当前实际：未运行，待验证。

## B：一次性令牌检查

- **前置条件**：确认真实接口认证方式；持有有效教师 Bearer 的测试客户端。
- **操作**：核对一次性令牌是否签发、缺失/重放是否拒绝。该检查与攻击页是否能获得 Bearer 是不同问题。
- **可观测结果**：课程预期缺令牌被拒、重复使用被拒；当前源码没有该机制，记录为课程能力缺口，不在本轮新增机制。
- 首次实际/当前实际：源码确认机制不存在；动态对照未执行，不计绿。

## C：SameSite 单独记录

- **前置条件**：真实登录响应可检查，不记录令牌正文。
- **操作**：查看 Set-Cookie；若有与身份有关 Cookie，核对 SameSite、Secure、HttpOnly 以及是否可替代 Bearer。
- **可观测结果**：课程预期会话 Cookie 有明确 SameSite；当前无 Cookie 认证的设计不能产生该项通过证据。
- 首次实际/当前实际：源码未设置认证 Cookie；浏览器响应待验证。判定为架构差异/课程缺口，不能写“双道防护通过”。

证据格式：场景 ID｜来源站点/目标站点｜身份模式｜响应状态｜数据差异｜Cookie 属性（不含值）｜提交号｜时间｜操作者。各子项分别判定，不合并成无依据的绿项。


# 修复后复测：2026-11-11

当前状态：已执行并通过，已由 test_injection.py 接入 make check；原“尚未执行/未接入”文字属于首次记录。

- **前置条件**：同原记录，使用临时数据库与本机 Chrome。
- **操作**：重放固定场景 test_csrf_replay_and_production_cookie / test_csrf_cross_site_form。
- **可观测结果**：真实另站 localhost 表单提交到 127.0.0.1 返回 401、资料仍为 0；有效 Bearer 缺令牌 403；首次令牌 200、重放 403；Cookie 包含 HttpOnly/Secure/SameSite=Strict。

证据：reports/evidence/injection-final.txt、make-check-final.txt。CSRF 机制是本轮明确授权后新增，与首次 Bearer-only 架构区别记录，不把无认证 Cookie 算作 SameSite 通过。
