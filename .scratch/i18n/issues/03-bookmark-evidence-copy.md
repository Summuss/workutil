# 03: Bookmark / Evidence 界面文案翻译

**What to build:** 把 `features/bookmark/` 与 `features/evidence/` 里所有硬编码中文文案替换成 `t(key)` 调用,`zh.json`/`ja.json` 补上对应的 key 与翻译。和票 02 是同一件事的另一半,分开是因为两边加起来文案量大,拆开 diff 更小、更容易审。

Evidence 这边文案面最广:Evidence / Case / Block(文字、图片、表格三种)的增删改界面、表格粘贴后的确认提示(「识别为表格,8 行 5 列 · 改为纯文字」)、导出按钮等。**导出的 Excel 文件本身(文件名、sheet 名、单元格内容)不在这次范围内**——文件名已有独立的日语命名约定(`エビデンス_<title>.xlsx`),sheet 名和单元格内容来自用户录入,两者都不受这个语言开关影响(spec.md「不受影响的部分」)。

已知的硬编码文案位置(实现时以实际代码为准):`BookmarkForm.tsx`(字段标签、按钮)等。

**Blocked by:** 01

**Status:** closed

- [x] `features/bookmark/**`、`features/evidence/**` 里的硬编码中文全部替换为 `t(key)`
- [x] `zh.json`/`ja.json` 补全这些 key,两边都有对应翻译
- [x] 切到日语,过一遍 bookmark 与 evidence 的每个页面(含分组、Case/Block 编辑、表格粘贴确认提示),没有遗留中文
- [x] 确认 Excel 导出的文件名与内容未被这次改动影响(仍是既定的日语文件名约定 + 用户原始内容)
- [x] key 对齐测试仍然通过
- [x] `make check` 与 `pnpm build` 通过
