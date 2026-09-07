# 01: 应用外壳与路由

**What to build:** M2 之后工具不止一个功能了,需要一层顶部导航。引入 react-router,`/` 是 memo,`/evidence` 是 evidence 列表。

**这张 ticket 是整个 M2 里唯一会碰 memo 的地方,而它有一条不能破的约束**:requirements.md F1 的核心卖点是「打开工具时光标已经在输入框里,零导航点击」。加了路由之后 `/` 必须**直接就是 memo 页、输入框已聚焦**,不能多一次跳转、不能先闪一下导航再渲染。这条卖点是 F1 存在的理由,不能被一次基础设施改造顺手弄丢。

选 react-router 而不是自己用 useState 切 tab:evidence 有三级导航(列表 → 某份 → Case),自己做等于手写一遍浏览历史;M3/M4 还有三个功能要进来。

**Blocked by:** —

**Status:** ready-for-agent

- [ ] 引入 react-router,`/` → memo,`/evidence` → evidence 列表(本 ticket 里先放一个空壳页)
- [ ] 顶部有导航,能在两个功能间切换,当前位置可辨
- [ ] **打开 `/` 时输入框已经聚焦**,和加路由之前完全一样
- [ ] 浏览器前进后退在两个页面间正常工作
- [ ] `pnpm build`(含 `tsc --noEmit`)通过
