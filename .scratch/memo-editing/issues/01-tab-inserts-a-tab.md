# 01: `Tab` 在 memo 输入框里打出制表符

**What to build:** `MemoComposer` 与 `MemoItem` 编辑态两个 `<textarea>` 里,`Tab` 插入一个真的 `\t` 并替换选区。

**用 `document.execCommand("insertText", false, "\t")`,不要用 `setState`。**

直接 `setState` 改字符串会**清空浏览器原生的撤销栈** —— `Ctrl+Z` 从此在这个框里失效,而 memo 输入框是全项目打字最多的地方。`execCommand` 已被标记 deprecated,但它是保住撤销栈的唯一办法(自建撤销栈要重新实现光标、选区、合并粒度一整套)。返回 `false` 时退回 `setState`,那时坏掉的是撤销,不是输入。

**不做多行缩进、不做 `Shift+Tab` 反缩进。** 选中多行按 `Tab`,行为是「选区被一个制表符替换」。多行缩进要处理选区扩展、行边界、撤销粒度,是另一个量级的功能,而这里要的只是「能打出制表符」。

**键盘出口:** `Tab` 被吃掉之后必须有别的办法离开输入框。

- `MemoItem` 编辑态:维持 `Esc` 的既有语义(退出编辑、**保留草稿**、头部标「未保存」),不改。
- `MemoComposer`:现在**没有任何退出键**,加 `Esc` = `blur()`,**不清空内容**。之后 `Tab` 恢复正常移焦。

**evidence 的 `BlockTextArea` 明确不动。** 制表符是它判断「这段粘贴是不是表格」的判据(有制表符且多行,design.md §6 F5),手打的 Tab 会污染那道粗筛。

**Blocked by:** 无

**Status:** ready-for-agent

- [ ] `MemoComposer` 与 `MemoItem` 编辑态里 `Tab` 插入 `\t`,焦点不移走
- [ ] 选中一段文字按 `Tab`,选区被一个制表符替换
- [ ] **连按几次 `Tab` 之后 `Ctrl+Z` 能一下一下撤销回去**
- [ ] `execCommand` 返回 `false` 时退回 `setState`,输入仍然正确(撤销失效可接受)
- [ ] `MemoComposer` 里 `Esc` 使焦点离开且**内容不清空**,之后 `Tab` 正常移焦
- [ ] `MemoItem` 编辑态的 `Esc` 行为**无变化**(退出编辑、草稿保留、标「未保存」)
- [ ] `Ctrl+Enter` / `Cmd+Enter` 保存的既有行为不受影响
- [ ] **evidence 的 `BlockTextArea` 里 `Tab` 行为不变**(焦点移走)
- [ ] `pnpm build` / `tsc` 通过;手动验证撤销那一条
