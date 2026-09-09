# 01: 说明字段、接口,以及那条不可逆的迁移

**What to build:** `todos.description`(`Text`,default `""`),配套的接口改动,以及**一条同时做三件事的迁移**。

**迁移里三步的顺序不能换:**

1. 加 `description` 列
2. 凡 `source_memo_id` 非空**且那条 memo 仍然存在**的 todo,往它的 `description` 追加一行 `[原 memo](/memo/N)`(说明本来是空的,所以就是写进这一行;若已有内容则空一行再追加)
3. drop `source_memo_id`

**第 2 步是整个 M7 里唯一不可逆的地方。** 顺序错了、或者忘了做,那些从 memo 转出来的待办就永久失去了回溯线索 —— 而 memo 还在,只是没人知道是哪条。指向已删 memo 的那些**不写**(链接点进去是 404,不如没有)。

这一步同时把 `/memo/:id` 的 UI 入口还了回来:拆掉徽章之后全前端没有任何地方链接过去了。所以那条路由**保留**,不要顺手删掉 `SingleMemoPage`。

**接口:**

- `TodoCreate` 加 `description: str = ""`;`TodoUpdate` 加 `description: str | None = None` —— `None` = 不改,`""` = 清空。**不要**照抄 `due_date` 那套 `model_fields_set` + `update_due_date` 的 sentinel:`due_date` 需要它是因为 `null` 本身就是合法目标值,而空字符串和「没传」在这里天然可分。
- `TodoRead` 带 `description` 全文,`GET /api/todos` 的列表也带。说明是纯文本、没有图片,体积有上界。
- 删掉 `source_memo_id` 之后,`router.py` 里 `get_existing_memo_ids`、`_to_read(todo, valid_memo_ids)`、`_single_read` 那一整套过滤跟着删,`_to_read` 退回一行 `TodoRead.model_validate(todo)`。`service.get_existing_memo_ids` 也删 —— 它是全后端唯一一处 `todo` 模块 import `memo` 模块的地方,删掉之后两个模块彻底无关。

**Blocked by:** 无

**Status:** ready-for-agent

- [ ] `todos.description`(`Text`,default `""`,非空)
- [ ] 一条迁移,三步顺序如上;`downgrade` 里 drop `description`、加回 `source_memo_id`(值补不回来,这是知情的)
- [ ] `TodoCreate.description` / `TodoUpdate.description` / `TodoRead.description`
- [ ] `service.create_todo` / `update_todo` 处理说明;`update_todo` 的 `None` 与 `""` 语义正确
- [ ] `router.py` 拆掉 `valid_memo_ids` 那一整套,`service.get_existing_memo_ids` 删除
- [ ] `backend/app/modules/todo/` 不再 import `app.modules.memo` 的任何东西
- [ ] 测试:创建时带说明、不带说明(空字符串)
- [ ] 测试:`PATCH` 传 `None` 不改说明、传 `""` 清空说明、传内容则替换
- [ ] 测试:列表返回说明全文
- [ ] **测试:迁移接住旧链接** —— 造三条 todo(指向存在的 memo / 指向已删的 memo / `source_memo_id` 为空),跑迁移,断言只有第一条的说明里多了 `[原 memo](/memo/N)`
- [ ] `make check` 与 `make test` 通过
