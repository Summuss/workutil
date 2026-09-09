# 03: 拆掉 memo 转 Todo 的前端入口与回溯徽章

**What to build:** 删掉 `ConvertToTodoModal.tsx`、`MemoItem` 工具条上的「转 Todo」按钮、`TodoItem` 上的「从 memo 而来」徽章链接,以及它们的 i18n key。

**这不是「功能不好用所以砍掉」。** 当初要带过去的本来就是那段描述,而不是那条 memo;Todo 有了自己的说明之后,绕经 memo 这一步没有理由了。理由记在 [ADR-0012](../../../docs/adr/0012-a-todo-description-is-not-a-memo.md)。

**两件容易顺手做错的事:**

1. **`firstLine.ts` 不要删。** 它当初是为「预填 memo 首行」写的,但折叠态 memo 的首行显示也在用(`MemoItem.tsx`)。`firstLine.test.ts` 一并保留。
2. **`/memo/:id` 与 `SingleMemoPage` 不要删。** 拆掉徽章之后它在应用内一度没有入口(全前端只有 `TodoItem.tsx:264` 一处链接过去),但票 01 的迁移会往 Todo 的说明里写 `[原 memo](/memo/N)` —— 入口当场就回来了。`SingleMemoPage` 的 `navigate(-1)` 返回逻辑也保持不变,它对新的入口一样成立。

拆完之后 `features/memo` 不再 import `features/todo` 的任何东西 —— 那处「知情的例外」随之消失,可以从 design.md 的记载里读到它的下场(已同步)。

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] `ConvertToTodoModal.tsx` 删除
- [ ] `MemoItem` 展开态工具条上的「转 Todo」按钮与相关 state 删除
- [ ] `TodoItem` 上的「从 memo 而来」徽章与 `Link` 删除,`Todo` 类型里的 `source_memo_id` 删除
- [ ] `features/memo` 不再 import `features/todo` 的任何东西
- [ ] `zh.json` / `ja.json` 里 `memo.to_todo`、`todo.from_memo`、`todo.view_source_memo` 等 key 两边一起删,key 对齐测试通过
- [ ] **`firstLine.ts` 与它的测试保留**,折叠态 memo 首行显示不受影响
- [ ] **`/memo/:id` 路由与 `SingleMemoPage` 保留**,直接敲地址仍能打开,「返回」行为不变
- [ ] `pnpm build` / `tsc` 通过
