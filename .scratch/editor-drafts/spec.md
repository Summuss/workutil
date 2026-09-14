# 草稿:编辑到一半的东西不能没

## 起因

memo 编辑到一半误按 `Esc`,写的全丢。查下来病根不在 `Esc` 的处理,在 `MemoItem` 的一个 effect:

```js
useEffect(() => {
  if (!editing) { changeDraft(memo.body); }   // editing: true→false 时也会跑
}, [memo.body, editing]);
```

`setEditing(false)` 之后它立刻用 `memo.body` 盖掉草稿。而代码注释、提示文案(「Esc 收起编辑」)、以及那个「未保存」角标**全都在描述一个不存在的行为** —— 角标因此永远不可能亮。`.scratch/memo-editing/issues/01` 当初也白纸黑字写着「维持 `Esc` 的既有语义(退出编辑、**保留草稿**、头部标「未保存」)」。

## 定下来的

- **草稿的单位是「一次编辑」,不是一个输入框。** 为了改一件事而打开的那一整块,整块都是一份草稿。Todo 的编辑表单里标题(单行)和说明(多行)因此**一起留** —— 按「多行留、单行丢」执行会造出上半截旧、下半截新的东西,比全丢更坏。
- **没有草稿的只有独立的单行编辑**:`InlineEdit`(用例编号、Block 小标题、Evidence 标题)。那是「双击、改一个词、回车」,重打接近零成本。
- **草稿活到保存成功或被明确放弃为止**,存 localStorage,活过刷新和关掉浏览器。
- **`Esc` 和「放弃」拆开**:`Esc` = 收起(留);按钮从「取消」改名「放弃」= 扔掉,草稿与已保存内容不同时先问一次。
- **陈旧草稿自净**:草稿连同「写下它时那份已保存的内容」一起存,读回来对不上就丢掉草稿。不写清理任务。

覆盖三处:memo 正文、Todo 编辑表单、Evidence 文字块。

## 相关文档

- [CONTEXT.md](../../CONTEXT.md) 的 **草稿(Draft)** 词条
- [design.md §6 F1](../../docs/design.md)
- [requirements.md §4 F1 / F2 / F5](../../docs/requirements.md)
