# 02: 展开一条 Memo,以 Markdown 呈现并就地编辑

**What to build:** 让列表里的 Memo 可以被展开查看完整内容,并且就地修改。

展开后看到的是渲染后的 Markdown —— 报错堆栈和命令行以代码块的等宽字体呈现并带语法高亮,这是这个工具对开发者最直接的价值。展开与编辑之间不设「查看态 → 点编辑」这一步,点开即可改。

Memo 内容大量来自外部粘贴(网页、Slack、错误页面),因此渲染必须禁用内嵌 HTML:页面脚本可以直接访问本机后端,而该后端在后续里程碑中会具备执行任意 Python 的能力,这条链必须在此切断。

**Blocked by:** 01

**Status:** done

- [x] 点击列表中的 Memo 就地展开,不发生路由跳转
- [x] 展开后显示渲染后的 Markdown,而非原始文本
- [x] 代码块以等宽字体显示并带语法高亮
- [x] 正文中的 HTML 标签与 script 作为**纯文本显示**,不被浏览器执行
- [x] 展开状态下可直接编辑正文并保存
- [x] 编辑区是纯文本框,不是所见即所得编辑器
- [x] 保存后内容更新,修改时间被记录
- [x] 编辑一条旧 Memo 后,它在列表中的**位置不变**(排序依据仍是创建时间)
- [x] HTTP 接缝测试:读取单条 Memo、更新正文、以及更新后列表顺序不变
- [x] HTTP 接缝测试:含 HTML 的正文原样存储与返回(是否执行由前端渲染保证)

## Comments

代码已实现,后端测试增至 20 条全绿(ruff / mypy / tsc 均干净),API 与静态构建产物验证通过。

- **后端**:
  - `schemas.py`: 新增 `MemoUpdate(body: str)`。
  - `service.py`: 新增 `get_memo(session, memo_id)` 与 `update_memo(session, memo_id, body)`，更新正文并刷新 `updated_at`。
  - `router.py`: 新增 `GET /api/memos/{memo_id}` 与 `PATCH /api/memos/{memo_id}` 路由。
  - `tests/test_memo_api.py`: 在主接缝上补充覆盖单条读取、正文更新、修改时间记录、空正文拒绝、修改后列表排序稳定性，以及 HTML 原样存取的测试。
- **前端**:
  - 引入 `react-markdown`、`rehype-highlight` 与 `highlight.js` (GitHub 风格)。
  - `MemoMarkdown.tsx`: 渲染 Markdown，代码块使用等宽字体并语法高亮；默认对 HTML 标签进行文本转义，防止 XSS 执行。
  - `MemoItem.tsx`: 点击单行就地展开/折叠，无路由跳转；展开后以两段呈现：上方渲染 Markdown，下方纯文本 `<textarea>`，无需经过「查看态 → 点编辑」即可就地修改，支持 `Ctrl+Enter` 快捷键或点击保存，展示创建及修改时间。
  - `MemoPage.tsx` / `MemoList.tsx`: 更新 Memo 后就地替换状态，保持在列表中的原位置不变。


---

**Review 后的修正**(`/code-review` 于 5b3c27f 之后)

发现的问题与处理:

1. **修改时间的测试是空的** —— `assert updated["updated_at"] >= created["updated_at"]` 的 `>=` 允许相等,把 `service.update_memo` 里的 `memo.updated_at = utc_now()` 删掉后 20 条测试依然全绿,验收条件「修改时间被记录」零保护。改为解析成 `datetime` 后严格 `>`(字符串比较也不可靠:整秒时间戳序列化时不带小数部分,`…:37Z` 会排在 `…:37.1Z` 之后)。已用变异验证:删掉那行现在会红。
2. **`ruff format` 未通过** —— 三个文件。根因是 `make check` 只跑 `ruff check`,已把 `ruff format --check` 加进去;同时给 alembic 生成的迁移文件加 format 排除,与既有的 `E501` 豁免一致。
3. **保存期间输入的字符会被吞** —— `MemoItem` 的 `useEffect([memo.body])` 在响应回来时覆盖本地草稿。`MemoComposer` 专门处理过同一个 race,这里反着来。改为在 `save()` 里显式判断:飞行期间没动过才用服务端返回值替换。
4. **`isModified` 的 1000ms 魔法数** —— 创建时两个时间戳来自同一次 `utc_now()`,严格相等,改为 `!==`。
5. **service 里两套 not-found 写法** —— `get_memo` 返回 `None`、`update_memo` 抛异常。统一成都抛 `MemoNotFound`,基类由 `Exception` 改为 `LookupError`。这个模块是后面四个功能的模板,不一致会被复制四遍。
6. **`getMemo` 是死代码** —— 前端封装无人调用(列表已带全文),删掉。后端 `GET /{id}` 是本 ticket 要求的接缝,保留。
7. **展开后正文显示了两遍** —— 原实现「渲染 + textarea」并列,纵向翻倍。改为只显示渲染态,**在正文上点一下整块换成 textarea**,光标落末尾;没有「编辑」按钮,那一下点击本来就是放光标的动作。`Ctrl+Enter` 存完退回渲染态,`Esc` 退回但保留草稿并在头部标「未保存」。
8. bundle 从 198 KB 涨到 499 KB(rehype-highlight 默认打包 highlight.js common 语言集)—— 本机加载,**决定不管**。
9. **展开只能用鼠标** —— 折叠行改成 `<button>`,渲染态正文加 `role="button" tabIndex=0` + Enter/Space,`Tab` 可达。正文里的链接点击不会误入编辑态。
10. **时间不显示年份** —— 去年 9/7 和今年 9/7 长得一样,加上年份(spec #21 靠时间定位)。
11. design.md §2 选型表补 Markdown 渲染一行;§6 F1、spec.md Testing Decisions、running.md 人工检查表同步更新。
12. **raw HTML 那条安全边界没有守卫** —— 刻意破一次「前端不写自动化测试」的例,加 vitest + `MemoMarkdown.test.tsx`(4 条渲染断言)。已用变异验证:给 react-markdown 加上 `rehype-raw` 后 2 条立刻红。

---

**用了一天之后的回退:编辑不再由点击正文进入**

上面第 7 条(点正文原地转编辑)在真实使用中不成立:**从 memo 里复制文本是每天都在做的动作**,
而拖选文字的「按下 → 拖动 → 松开」会被当作一次点击,于是选区当场消失、界面跳进编辑态。

改为:展开后是渲染态,正文不响应任何点击;编辑由头部的「编辑」按钮进入。

这不违反本 ticket「不设「查看态 → 点编辑」这一步」的初衷 —— 那条针对的是**页面跳转**
(spec #19 原文是「不需要经过『查看页 → 点编辑』两次跳转」)。展开与编辑始终在同一张卡片里,
导航点击数仍然是零。已把这个理由写进 design.md §6 F1 与 spec.md,免得以后又被改回去。

键盘路径相应改为:`Tab` 到某条 → `Enter` 展开 → `Tab` 到「编辑」→ `Enter` 进编辑。

---

**Review 02~06 时的连带修正**

`router.py` 的 docstring 写着「Forwarding only」,但到票 06 为止它已经手工拼了 5 次 `MemoRead`,还自己调 `count_images` 和 `extract_snippets` —— 而 spec 说「HTTP 路由层不单独测试,它只做转发」,于是这些逻辑没有任何直接测试覆盖。已把组装收进 `MemoRead.of()`、把列表与搜索合并成 `service.list_memos(session, images_dir, query)`,路由重新变回一行转发。这个模块是后面四个功能要照抄的模板,所以这条值得改。
