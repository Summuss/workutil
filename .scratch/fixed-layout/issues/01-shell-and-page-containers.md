# 01: 固定外壳与各页滚动区

**What to build:** 把外壳从「页面自然变长、整窗滚动」改成「一屏高、滚动下放到内容区」,并给七个页面各自划出固定区与滚动区。

`App.tsx` 的 `min-h-screen flex-col` 改成 `h-dvh overflow-hidden flex-col`;导航条已经是 `shrink-0`,不动。每页的 `<main>` 从「一个既限宽又负责高度的 flex 容器」拆成两层:外层 `flex-1 min-h-0` 负责撑满与滚动,内层 `mx-auto max-w-3xl` 负责限宽与内边距。四页宽度从 `max-w-2xl`(672px)统一到 `max-w-3xl`(768px)。

**`min-h-0` 是这次唯一的常驻陷阱**:flex 子项的 `min-height` 默认是 `auto`,漏写一个,内容会把容器撑破、滚动条又长回窗口上,而症状看起来像「改动没生效」。每一个「要滚的 flex 子项」都要显式写。

七个页面里 Evidence 详情最复杂(固定头 + 固定底 + 中间滚),它单独放在 ticket 02;这一条先把其余六个和外壳做完,并把 Evidence 详情**至少**改成不再整窗滚动。

划分见 `spec.md` 的表格。Memo 页要注意:输入框钉住之后,「打开即聚焦、`Ctrl+Enter` 保存、保存后仍聚焦」这条 F1 的核心路径不能受影响。

**Blocked by:** 无

**Status:** ready-for-agent

- [ ] `App.tsx` 改 `h-dvh overflow-hidden`,窗口不再出现滚动条
- [ ] 抽一个共享的页面布局组件(固定区 / 滚动区两个 slot),七个页面共用,不各写一遍两层 div
- [ ] Memo(`/`):输入框 + 搜索栏钉顶,memo 列表滚
- [ ] Memo 详情(`/memo/:id`):返回行钉顶,正文滚
- [ ] Todo(`/todos`):新增输入框钉顶,列表滚
- [ ] Bookmark(`/bookmarks`):「登记书签 / 新建分组」按钮行钉顶,分组与散装列表滚
- [ ] Evidence 列表(`/evidence`):新建按钮行钉顶,列表滚
- [ ] Evidence 详情(`/evidence/:id`):先做到「内容在自己的容器里滚、窗口不滚」,精细划分交给 02
- [ ] 四页宽度从 `max-w-2xl` 改到 `max-w-3xl`,七个页面内容左右边界一致
- [ ] 每个滚动容器的祖先链上该写 `min-h-0` 的都写了 —— 逐页验证:内容超长时滚动条出现在**内容区**而不是窗口
- [ ] Memo 页「打开即聚焦输入框」「保存后仍聚焦」不受影响
- [ ] 不加任何响应式断点
- [ ] `make check` 通过
