# 09: Memo 列表记住展开状态,刷新后保持

**What to build:** `MemoList` 的展开状态(`expandedIds`)目前只在内存里,刷新页面或离开再回来就丢失。改成持久化到 localStorage,按 memo id 记忆,刷新后展开过的 memo 保持展开。

只做 `MemoList` 这一处。`SingleMemoPage` 有自己独立的展开状态(默认恒为 `true`),这是详情页「点进去就要看全文」的刻意设计,和列表页的「预览/展开」语义不是一回事,不共用这份持久化状态。

沿用项目里唯一的既有 localStorage 用法(`shared/i18n/index.tsx`)的写法惯例:读写都判断 `typeof window !== "undefined" && window.localStorage` 并包一层 try/catch(localStorage 可能不可用或被浏览器拦截)。

**Blocked by:** 无

**Status:** resolved

- [x] `MemoList` 的 `expandedIds` 展开/折叠时写入 localStorage(按 memo id)
- [x] `MemoList` 挂载时从 localStorage 读回展开状态,而不是每次都从空集合开始
- [x] localStorage 读写按既有惯例做防御性处理(window 存在性判断 + try/catch),不可用时静默降级为「不记忆」,不报错、不崩溃
- [x] 展开某条 memo 后刷新整个页面,它保持展开
- [x] `SingleMemoPage` 的展开状态不受影响,仍然默认恒为展开
- [x] `.scratch/memo/spec.md` 的 Implementation Decisions §前端 补一条,说明展开状态持久化到 localStorage(项目里第二个用到 localStorage 的地方,跟随 i18n 的既有写法)
- [x] `pnpm build`/`tsc` 通过;手动验证刷新后展开状态保持
