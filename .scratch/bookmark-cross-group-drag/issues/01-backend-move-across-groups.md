# 01: 后端「移到某个组的第 N 位」原子接口

**What to build:** 扩展书签的 move 端点,让一次请求同时表达「换到哪个组」和「落在第几位」:请求体带上 `group_id`(目标组 id,或 `null` 表示散装区)。服务端在一个事务里改归属、给目标组的兄弟重排,**并给原来那组的兄弟收拢序号** —— 书签走了之后原组留下 `0,1,3` 这样的空洞,而 `Ordered` 契约要求从 0 连续。

**不要改 `app/core/ordering.py` 的 `MoveRequest`。** 它被 todo、evidence、bookmark 三个模块共用(各自 `schemas.py` re-export),加一个 `group_id` 等于让 todo 和 evidence 也长出一个它们没有的概念。在 bookmark 模块里定义自己的请求 schema。

**不走「先 PATCH `group_id` 再 move」两步。** 中间态是真实的:归属改完、排序失败,书签就落在新组末尾而不是松手的位置;而且前端的乐观回滚要处理两个列表两次失败。

`to` 沿用现有的钳制语义(越界夹到 `[0, len-1]`),不算错误。

**Blocked by:** 无

**Status:** ready-for-agent

- [ ] bookmark 模块新增自己的移动请求 schema(带 `to` 与 `group_id`),`core/ordering.py` 的 `MoveRequest` **不动**
- [ ] `service.move_bookmark` 支持跨组:改 `group_id`、目标组重排、**原组收拢序号**,一个事务
- [ ] `group_id: null` 表示移到散装区,是合法目标
- [ ] 目标组不存在 → 404
- [ ] 端点返回受影响的两个列表(原组 / 目标组,散装区算一个),前端一次拿全
- [ ] 测试:散装 → 组、组 → 散装、组 A → 组 B、移进空组
- [ ] 测试:移动后**原组**的 `order` 从 0 连续,没有空洞
- [ ] 测试:目标组的 `order` 从 0 连续,书签落在请求的位置
- [ ] 测试:`group_id` 等于当前组时,行为与改造前的同组内移动一致(回归)
- [ ] 测试:`to` 越界被钳制,不报错
- [ ] `make check` 通过
