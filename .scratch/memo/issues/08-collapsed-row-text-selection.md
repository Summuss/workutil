# 08: 折叠态 Memo 允许直接拖选文字复制

**What to build:** `MemoItem` 折叠态时整行是一个 `<button>`(`onClick` 直接绑在按钮上),拖选文字复制和点击展开命中同一个事件,导致想复制一段文字时行会意外展开。展开态已经因为同样的问题从「整卡片点击」改成了「专门按钮」(见 `.scratch/memo/issues/02-expand-and-edit-a-memo.md` 底部「用了一天之后的回退」那段记录),折叠态用同一套思路解决,不新发明一套启发式判断。

改成:折叠态整行不再是 `<button>`,首行文字是纯文本、可自由拖选;另外放一个独立的展开图标按钮(`ChevronDownIcon`,已存在于 `shared/icons.tsx`,不用新画),点它才触发展开 —— 和展开态的 `ChevronUpIcon` 对称。

**Blocked by:** 无

**Status:** todo

- [ ] 折叠态整行不再是 `<button>`,首行文字所在容器不响应点击
- [ ] 折叠态新增一个 `ChevronDownIcon` 图标按钮,点击触发展开(`onToggleExpand`)
- [ ] 折叠态下可以用鼠标拖选首行文字并复制,不会触发展开
- [ ] 展开图标按钮本身保持键盘可达(Tab 可达、Enter/Space 触发)
- [ ] 搜索结果片段(snippet)的展示与可选中性不受影响(它已经在按钮外面,见 `MemoItem.tsx:196-214` 的既有注释)
- [ ] `.scratch/memo/spec.md` 里 User Story #19(「点击列表里某条就地展开」)与 Implementation Decisions §前端 的对应描述同步更新,反映「展开也改为专门按钮触发,不再是点击整行」
- [ ] `pnpm build`/`tsc` 通过;手动验证折叠态拖选复制不再意外展开
