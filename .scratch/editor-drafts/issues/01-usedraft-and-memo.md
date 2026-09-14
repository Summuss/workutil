# 01: `useDraft` 与 memo 正文

**Status:** resolved

**Blocked by:** 无

**What to build:** 一个共用的 `shared/useDraft.ts`,并把 memo 的编辑态接上去。

**hook 的形状**:`useDraft(key, saved)` 返回 `{ draft, setDraft, isDirty, discard, commit }`。

- `key` 是 localStorage 的键(memo 用 `draft:memo:<id>`)。
- 存进去的是 `{ draft, savedAt }`,**`savedAt` 是写下这份草稿时那份已保存的内容**。读回来时 `savedAt !== saved` 就丢掉草稿并清键 —— 这一条同时盖掉「另一个标签页改过」「这条被删了、id 日后被复用」「放了太久」三种情况,所以**不要另外写扫垃圾的逻辑**。
- localStorage 可能不可用或被禁,读写都要 try/catch 并静默降级(照抄 `shared/i18n/index.tsx` 与 `features/memo/MemoList.tsx` 的既有写法)。
- `commit()` 在保存成功后清键。

**memo 侧要改的**:

- **删掉 `MemoItem` 里那个 `[memo.body, editing]` 的 effect**,它就是病根。「服务器更新不要踩掉正在打的字」这个它原本要解决的问题,改由 `isDirty` 判断:不脏时跟随 `memo.body`,脏时不动。
- `Esc` 维持 `setEditing(false)`,草稿留着。
- 「取消」按钮改名**「放弃」**,调 `discard()`;`isDirty` 为真时先 `window.confirm` 一次,为假时直接关。
- 「未保存」角标改由 `isDirty` 驱动 —— 它现在会真的亮起来。折叠态和展开态两处都要。
- **收起之后正文仍然渲染已保存的内容**,不是草稿。展开看到的是「记录里现在是什么」,角标负责说「另外还有一版没存」。

**明确不动**:`MemoComposer`(它的 `Esc` = `blur()`,内容本来就不清空,没有「已保存内容」可比,不接 `useDraft`);`InlineEdit`(单行,没有草稿);`SingleMemoPage` 走的是同一个 `MemoItem`,跟着一起好。

- [x] 编辑一条 memo 写几个字,按 `Esc` → 编辑器收起,卡片标「未保存」,正文显示的仍是已保存的内容
- [x] 接着**刷新页面**,点编辑 → 刚才写的还在
- [x] 点「放弃」→ 先问一次,确认后草稿没了,角标灭,再点编辑是已保存的内容
- [x] 没改过内容时点「放弃」→ 不问,直接关
- [x] 保存成功后角标灭,localStorage 里那个键没了
- [x] 搜索把这条过滤掉再搜回来、切到 Todo 再切回来,草稿都还在
- [x] 在另一个标签页改了这条 memo,回到这个标签页 → 草稿被丢弃(`savedAt` 对不上),显示的是新的正文
- [x] 禁用 localStorage 的浏览器里,编辑/保存/放弃全部正常,只是草稿不跨刷新
- [x] `pnpm build` / `tsc` 通过
