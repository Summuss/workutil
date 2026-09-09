# 07: Memo 详情页「返回」改用浏览器历史回退

**What to build:** `SingleMemoPage` 的返回链接目前硬编码指向 `/`(memo 列表),这是 `.scratch/todo/spec.md`(§ 从 memo 转出)当初设计 `/memo/:id` 路由时定下的行为。但现在这条路由的入口不止 memo 列表本身,还有 Todo 卡片上「从 memo 而来」的链接(`todo.source_memo_id` 非空时,见 `TodoItem.tsx`)—— 从 Todo 点进 Memo 详情页后点「返回」,今天会回到 memo 列表而不是原来的 Todo 画面。

改成 `navigate(-1)`(浏览器历史回退):不管以后从哪个页面链接进 `/memo/:id`,「返回」都自然去正确的地方,不需要每加一个入口就单独处理。如果没有历史记录可退(比如直接打开 `/memo/:id` 的链接、新标签页里打开),兜底回 `/`(memo 列表)。

返回按钮的文案(「回到全部」/`すべてに戻る`,`memo.back_to_all` key)是指向性的,改成通用历史回退后不再准确,一并改成不指定目的地的通用文案(「返回」/「戻る」),`zh.json`/`ja.json` 同步改、保持 key 集合对齐。

**Blocked by:** 无

**Status:** todo

- [ ] `SingleMemoPage` 的返回操作改为 `navigate(-1)`
- [ ] 判断「没有应用内历史记录可退」的情况(例如直接打开 `/memo/:id`、新标签页打开),此时兜底 `navigate("/")`
- [ ] 从 Todo 卡片的「从 memo 而来」链接进入 Memo 详情页后点返回,回到原来的 Todo 画面(而不是 memo 列表)
- [ ] 从 memo 列表点进详情页后点返回,行为不变(仍回到列表)
- [ ] `memo.back_to_all` 文案改为通用的「返回」表达,`zh.json`/`ja.json` 同步更新且 key 对齐测试通过
- [ ] `.scratch/todo/spec.md` § 从 memo 转出 里「顶部「回到全部」」的描述同步更新
- [ ] `pnpm build`/`tsc` 通过;手动验证两条入口路径的返回行为
