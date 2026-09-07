# 04: Block 骨架与文字 Block

**What to build:** 三层模型的最下面一层。Block 表(`kind` / `order` / 可选 `label`)加上最简单的一种 kind —— 文字。**先用最简单的内容类型把 Block 的增删改与排序打通**,后面两种 kind 就只是往里塞不同的 payload。

**没有步骤编号。** 一个用例里的几段是分节(事前準備 / 画面 / ログ / DB 更新後の結果),不是 1→2→3;编号只会在插入一节时全部错位。每段用可选的 `label` 当小标题(见 ADR-0003)。

**Log 归进 `text`,不单列一类** —— 已确认不需要特殊排版。

排序交互是**上下移动 + 置顶 / 置底,不做拖拽**:Block 是边做边追加的,重排基本是就近修正;真要从底部搬到顶部,置顶一下解决。不值得为此引一个拖拽库并处理键盘可达性。

**Blocked by:** 03

**Status:** ready-for-agent

- [ ] `evidence_block` 表:`case_id` / `order` / `kind` / `label`(可空)+ 文字内容,以及 Alembic 迁移
- [ ] `kind` 的取值域是 `text` / `image` / `table`,本 ticket 只实现 `text`
- [ ] 在一个 Case 里加 / 改 / 删文字 Block
- [ ] 给 Block 加 / 改 / 清空 label
- [ ] 排序:上移 / 下移 / 置顶 / 置底,顺序在刷新后保持
- [ ] 删 Case 时它名下的 Block 一并消失
- [ ] HTTP 主接缝测试覆盖增删改与排序(含首尾边界:第一个上移、最后一个下移)
