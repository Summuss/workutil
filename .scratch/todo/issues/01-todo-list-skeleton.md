# 01: Todo 骨架

**What to build:** Todo 的表、增删改、列表、完成 / 撤销,以及页面本身。`registry.py` 加一行,`AppNav` 加一个 tab,路由 `/todos`。

**完成即从主列表移出,进一个默认折叠的「已完成」区** —— 验收要点要的是「已完成项不干扰未完成项的浏览」,划掉留在原地只是视觉上的不干扰,列表长了照样要滚过一堆划掉的行。存 `completed_at`(`completed_at` 有值即已完成),**不自动清理**:本地自用,一年也攒不到会拖慢查询的量,而「上周做完了什么」是白捡的。

**完成 / 撤销是两个独立动词**(`POST {id}/complete`、`POST {id}/reopen`),**不是** `PATCH {done: true}`。和 evidence 已经定型的写法一致:状态转移是动词,字段编辑才是 PATCH。而且 `complete` 要顺带写 `completed_at` —— 藏进通用 PATCH 里,迟早有人改了状态忘了时间戳。

**未完成项全量返回、不设上限**(看不见的待办等于不存在);**已完成区**按 `completed_at` 倒序 + 上限,沿用 memo / evidence 的 `RECENT_*_LIMIT` 做法。已完成区是唯一会无限增长、也是唯一不需要看全的地方。

录入要低摩擦:一个输入框,回车即存,不要求填别的字段。

**Blocked by:** —

**Status:** ready-for-agent

- [ ] `modules/todo/`(router / models / service / schemas)+ Alembic 迁移 + `registry.py` 一行
- [ ] `POST /api/todos`(只需要 title)/ `PATCH {id}`(改 title)/ `DELETE {id}`
- [ ] `GET /api/todos` —— 未完成全量 + 已完成(倒序、有上限)
- [ ] `POST /api/todos/{id}/complete` / `POST /api/todos/{id}/reopen`,`complete` 写 `completed_at`
- [ ] 前端 `/todos` 页面 + `AppNav` 一个 tab:输入框回车即存,已完成区默认折叠、可展开、可撤销
- [ ] 打开 `/` 仍然直接是 memo 输入框、光标已在里面
- [ ] 主接缝测试:未完成不受上限影响、已完成区受上限
- [ ] `make check` 与 `pnpm build` 通过
