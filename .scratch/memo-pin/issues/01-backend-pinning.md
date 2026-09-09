# 01: 后端置顶字段、端点与列表顺序

**What to build:** `memos` 表加 `pinned_at: datetime | None`(可空,带 index),Alembic 迁移一条。非空即置顶,值同时就是置顶区内的排序依据(最近钉的在最上)。

**不加 `order` 列。** memo 是全项目唯一没有显式顺序的实体,给它套上 `core/ordering.py` 的 `Ordered` 等于承认 memo 之间有先后关系 —— 那是 ADR-0008 明确不接受的。

**置顶集合必须是一次单独查询。** `list_memos` 现在只取最近 `RECENT_MEMO_LIMIT`(200)条,一条钉住但很旧的 memo 会落在第 201 条之后 —— 而「钉住一条三个月前的」正是这个功能的主要用法。默认列表 = `pinned_at DESC` 的置顶集合 + `created_at DESC, id DESC` 的最近 200 条,**后者要排除已在置顶集合里的**,否则刚写又被钉的那条会出现两次。

搜索路径(`_matching`)完全不动:置顶不参与排序、不参与过滤。

置顶开关用 `POST` / `DELETE /api/memos/{id}/pin` 两个幂等端点,而不是一个 toggle(toggle 在双击或重放时结果不确定)。**改置顶不动 `updated_at`** —— 那不是修改内容,否则「修改于」会为一次点击而出现。

**Blocked by:** 无

**Status:** ready-for-agent

- [ ] `memos` 表加 `pinned_at`(可空,index),Alembic 迁移一条,`make test` 能在空库和已有数据上都跑通
- [ ] `POST /api/memos/{id}/pin` 与 `DELETE /api/memos/{id}/pin`,返回更新后的 memo
- [ ] 列表响应带上 `pinned_at`
- [ ] 默认列表:置顶集合在前(`pinned_at` 倒序),其余按现有规则,两段**去重**
- [ ] 置顶集合不受 `RECENT_MEMO_LIMIT` 限制,不设条数上限
- [ ] 搜索路径不受置顶影响
- [ ] 测试:置顶 / 取消置顶是幂等的(重复调用结果一致)
- [ ] 测试:置顶不修改 `updated_at`;编辑内容不修改 `pinned_at`
- [ ] 测试:置顶不存在的 memo → 404
- [ ] 测试:**造 200 条以上 memo,置顶最旧的那条,它出现在默认列表里** —— 这个功能最容易悄悄坏掉的地方
- [ ] 测试:一条刚写又被置顶的 memo 在列表里**只出现一次**
- [ ] 测试:搜索结果的顺序与置顶无关(回归)
- [ ] `make check` 通过
