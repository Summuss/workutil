# 02: Markdown 渲染器提到 `shared/`

**What to build:** 把 `features/memo/MemoMarkdown.tsx` 搬成 `shared/Markdown.tsx`,`MemoMarkdown.test.tsx` 跟着搬,`MemoItem` / `SingleMemoPage` 改 import。

**为什么现在搬:** 票 04 要在 Todo 的说明里渲染 Markdown。留在原地就意味着 `features/todo` 依赖 `features/memo` —— 而 `.scratch/todo/issues/04-from-memo.md` 立过规矩:「前端 `features/memo` 单向依赖 `features/todo` 是知情的一处例外,**反向永远不许**」。票 03 正好在拆那条正向依赖,不该在拆的同一轮里留下反向的新债。

这和 M2 第一步把图片链路从 `memo/service.py` 提到 `core/images.py` 是同一个动作,理由 design.md §6 F5 记过:**共享的是机制,不是概念**。

**那条安全线必须一起搬。** `MemoMarkdown.test.tsx` 是全项目唯一破例写的前端自动化测试,守的是「禁用 raw HTML」—— memo 正文大量来自外部粘贴,而页面脚本能直接调用本机后端,后端具备执行任意本地代码的能力(ADR-0005)。给 react-markdown 加一个 `rehype-raw` 就能悄无声息接通这条链,而那是一行改动。换目录不能把它弄丢。

纯搬家,**不改渲染行为**。

**Blocked by:** 无

**Status:** resolved

- [x] `shared/Markdown.tsx`(组件名一并改成 `Markdown`),`features/memo/MemoMarkdown.tsx` 删除
- [x] `shared/Markdown.test.tsx` 搬过去并保持全绿
- [x] `MemoItem.tsx` / `SingleMemoPage.tsx` 改 import,渲染结果无变化
- [x] **变异验证**:给渲染器加上 `rehype-raw`,搬家后的测试**立刻变红**(和当初一样)
- [x] `pnpm build` / `tsc` 通过

## Comments

### Code Review
- **Standards**: 前端通用机制下沉至 `src/shared/`，解耦模块依赖，遵循项目既定架构规范。
- **Spec**: `MemoMarkdown.tsx` 与其安全测试成功迁入 `src/shared/Markdown.tsx` / `Markdown.test.tsx`，保持「禁用 raw HTML」安全防线，测试全部通过，`pnpm build` 成功。
