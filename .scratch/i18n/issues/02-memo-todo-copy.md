# 02: Memo / Todo 界面文案翻译

**What to build:** 把 `features/memo/` 与 `features/todo/` 里所有硬编码中文文案(按钮、占位符、空状态、确认弹窗等)替换成 `t(key)` 调用,`zh.json`/`ja.json` 补上对应的 key 与翻译。

两个模块一起做,是因为 M3 已经把它们绑在了一起(memo 卡片上的「转 Todo」按钮、`/memo/:id` 的回溯链接),文案上也有交叉,分开改容易漏。**不改这两个模块之外的任何文件**,也不碰后端 —— 后端错误信息是单独一张票(04)。

已知的硬编码文案位置(实现时以实际代码为准,不止这些):`MemoComposer.tsx`(占位符、保存按钮)、`TodoItem.tsx`(到期状态文案、按钮)等。

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] `features/memo/**`、`features/todo/**` 里的硬编码中文全部替换为 `t(key)`
- [ ] `zh.json`/`ja.json` 补全这些 key,两边都有对应翻译
- [ ] 切到日语,过一遍 memo 与 todo 的每个页面(含空状态、确认弹窗、to-Todo 转换弹窗),没有遗留中文
- [ ] key 对齐测试仍然通过
- [ ] `make check` 与 `pnpm build` 通过
