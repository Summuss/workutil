# 01: 后端支持绝对位置排序

**What to build:** 扩展 `backend/app/core/ordering.py` 的共享排序机制(`Move`/`reorder`/`renumber`),让调用方可以把一个元素移动到**任意目标位置**,而不只是 `up`/`down`/`top`/`bottom` 四个方向。`order` 字段已经是从 0 开始的连续整数,`top`/`bottom` 本来就是走「弹出-插入-整体重编号」这条路径跳到边界 —— 这次只是让调用方能传入一个具体目标位置,存储层不需要改。

同时移除 `Move.UP`/`Move.DOWN` 两个方向值:前端改造完(ticket 02-04)后,单步移动和任意位置移动都会走新的绝对位置参数,这两个方向值不再有调用方。个人工具、没有外部 API 消费者,不留没人调用的分支。

五个资源(Todo、BookmarkGroup、Bookmark、EvidenceCase、EvidenceBlock)的 `move_*` service 函数与各自的 `MoveRequest` schema 都要跟着透传新的参数 —— 但排序逻辑本身只改 `core/ordering.py` 一处。

**Blocked by:** 无

**Status:** todo

- [ ] `core/ordering.py`:`Move`/`MoveRequest` 相关类型扩展,支持「移动到绝对位置」(方向枚举里去掉 `up`/`down`,保留 `top`/`bottom`,新增一个可携带目标 index 的变体;或改成判别联合 —— 选一种把"方向"与"绝对位置"两种意图表达清楚的形状)
- [ ] `reorder`(或新增一个姊妹函数)接受目标位置,一次性完成「弹出-插入-整体重编号」,不改变现有 `top`/`bottom` 语义
- [ ] `Todo`、`BookmarkGroup`、`Bookmark`、`EvidenceCase`、`EvidenceBlock` 五个模块的 `move_*` service 函数与 `MoveRequest` schema 透传新参数
- [ ] 移除 `Move.UP`/`Move.DOWN` 及所有分支代码、以及五个模块里因此变成死代码的部分
- [ ] 五个 `POST .../move` 路由的请求体校验体现新形状(拒绝旧的 `up`/`down`)
- [ ] 主接缝测试(每个资源至少一条):移动到中间位置、移动到当前位置(应无变化)、移动到超出范围位置的边界处理
- [ ] 既有测试里引用 `up`/`down` 的用例改写或删除
- [ ] `make check` 通过
