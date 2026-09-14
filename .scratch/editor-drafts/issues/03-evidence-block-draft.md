# 03: Evidence 文字块的草稿

**Status:** resolved

**Blocked by:** 01

**What to build:** `BlockTextArea` 在**编辑既有文字块**时接 `useDraft`。

- key 用 `draft:block:<blockId>`,`saved` 是 `block.text`。
- `Esc` = 收起编辑器,草稿留着;`BlockCard` 上要有记号说明这个 block 有未保存的修改(和小标题、工具条挤在同一行,位置要想一下)。
- 收起后 `<pre>` 里渲染的仍然是**已保存的** `block.text`。
- 「放弃」的入口:编辑态里加,和 memo 同一套(`isDirty` 时问一次)。

**底部那个新增用的 composer 不接 `useDraft`。** 它和 `MemoComposer` 是同一类东西:没有「已保存内容」可比,`initial` 是空串,commit 之后回到空串继续粘 —— 那是它现在的正确行为。它的 `Esc` 没有 `onCancel`,本来就什么都不做,维持原样。

**别碰 `handlePaste` 那条判别顺序**(先问表格、再问图片)。它有自己的理由,和这条无关。

- [x] 编辑一个文字块写几个字,按 `Esc` → 收起,卡片上看得出有未保存的修改,`<pre>` 里还是已保存的文字
- [x] 刷新页面、切到别的用例再切回来 → 草稿还在
- [x] 「放弃」问一次,确认后回到已保存的文字
- [x] 保存成功后记号消失
- [x] 底部 composer 的行为**一点没变**:粘贴、`Ctrl+Enter`、commit 后清空并保持光标
- [x] `pnpm build` / `tsc` 通过
