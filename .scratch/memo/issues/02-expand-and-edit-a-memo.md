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

