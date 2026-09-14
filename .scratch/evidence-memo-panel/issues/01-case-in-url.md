# 01: 当前 case 进 URL

**Status:** resolved

**Blocked by:** 无

**What to build:** 路由加 `/evidence/:evidenceId/cases/:caseId`,`EvidenceDetailPage` 的 `pickedId` 改成读路由参数。

- **路径式,不是查询参数。** §2 已经把这件事写成「三级导航,URL 即状态」;用 `?case=12` 会让文档和实现说两种话,而这次改动的全部内容就是把已经写下来的设计补上。
- **切 tab 用 `replace` 而不是 `push`。** 后退仍然只跨越「列表 ↔ 某份 evidence」这一层。这是 `EvidenceDetailPage` 原注释里那条理由(「making every tab click a history entry would turn Back into "undo my last eight clicks"」)—— 它只否决了「tab 进历史」,没否决「tab 进 URL」,所以那条注释要改写而不是删掉。
- `/evidence/:evidenceId`(不带 case)继续有效,落到第一个用例,并 `replace` 成带 case 的形式。
- 现有那句「这个 case 不在了就退回第一个」的兜底(`cases.find(...) ?? cases[0]?.id ?? null`)原样保留 —— URL 里带着一个已删的 case id 走的就是这条路。
- 新建 / 复制用例之后要跳到新用例,删除用例之后落到顶上来的那个,行为都不变,只是现在体现在 URL 上。
- **别动 `CaseBlocks` 的 `key={selectedId}`**,切用例仍然要整个重来。

**明确不做:滚动位置的恢复。** block 列表里图片是异步的,恢复滚动在字节到齐之前必然落错地方 —— 「加完一段滚到它」那条逻辑已经为此踩过一次坑(它要等每一张 `<img>` 的 `load` 才敢滚)。

- [x] 停在第 3 个用例按 `F5`,回来还是第 3 个用例
- [x] 从导航条切到 Todo 再切回 Evidence 列表、点进同一份 → 进的是第一个用例(列表入口本来就不带 case,这是对的)
- [x] 直接把 `/evidence/7/cases/12` 贴进地址栏能打开
- [x] 连点五个用例 tab,按一次后退 → 回到 evidence 列表,不是上一个 tab
- [x] URL 里写一个不属于这份 evidence 的 case id → 落到第一个用例,不白屏不报错
- [x] 删掉当前用例 → 落到顶上来的那个,URL 跟着变
- [x] 复制用例 → 跳到副本并直接进入重命名(既有行为不变)
- [x] 后端 / 既有测试无需改动;`pnpm build` / `tsc` 通过
