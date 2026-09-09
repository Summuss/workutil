# 02: 文字 Block 的换行,逐行导出还是挤进一格

**What to build:** `evidence_block.split_lines`(`bool`,default `True`)+ 一条迁移 + `PUT .../blocks/<id>/split-lines` + 导出时的两条分支 + 工具条上的开关。

**开关挂在 Block 上,不是挂在导出时。** 它描述的是**内容是什么**(这段是逐行的日志 / 这段是一句说明),不是导出时的心情 —— 一份 evidence 里两种文字同时存在是常态,挂在导出上会强迫它们同命。这让它和表格 Block 的 `has_header` 成为同一类东西:**某个 kind 专属的一个布尔开关**。

**所以接口也长成同一个形状:`PUT .../blocks/<id>/split-lines`**,和 `PUT .../blocks/<id>/header` 对称,不塞进 `PATCH .../blocks/<id>`(那个只改正文)。对非文字 Block 是 422,和 `PATCH` 对图片 Block 的处理一致。

**导出的两条路:**

- **逐行(默认)**:每行写一个单元格,占 `len(lines)` 行,**不设 `wrap_text`**。一行 log 就该是一行;超长时向右溢出(文字 Block 右边本来就是空列)比折成 20 行高的一格好读,而且这和票 01 里「数据行不 wrap」是一致的。
- **合并**:仍是一格 + `wrap_text`,和现在完全一样。

**空行原样成为一个空 Excel 行** —— `"a\n\nb"` 是 3 行不是 2 行。空行是内容的一部分,evidence 的底线是「我看到的就是这个」。Block 之间空一行的规则不变(即逐行的 Block 之后仍然空一行再接下一个)。

**工具条上的开关只在该 Block 含 `\n` 时显示。** 不含换行时它没有任何含义,常驻只是噪音。

**默认值会改变既有 Block 的导出结果**:老的文字 Block 迁移后拿到 `True`,重新导出会变成逐行。**这是想要的** —— 那正是新行为,而 evidence 导出后使命即完成(ADR-0001),重导旧的极少见。

**Blocked by:** 无

**Status:** resolved

- [x] `evidence_block.split_lines`(`Boolean`,default `True`,非空)+ 一条迁移
- [x] `PUT /api/evidence/{eid}/cases/{cid}/blocks/{bid}/split-lines`,请求体一个布尔,返回更新后的 Block
- [x] 该端点对图片 / 表格 Block 返回 422
- [x] `BlockRead` 带上 `split_lines`
- [x] 导出:逐行时每行一格、占 `len(lines)` 行、不设 `wrap_text`
- [x] 导出:合并时一格 + `wrap_text`(与改动前一致)
- [x] 导出:空行原样成为空 Excel 行;Block 之间仍空一行
- [x] 前端:文字 Block 工具条上的开关,**只在正文含 `\n` 时显示**
- [x] 文案中日双份,key 对齐测试通过
- [x] 测试:三行文字逐行导出占三行,每行是独立单元格
- [x] 测试:同一段切到合并后占一行且 `wrap_text` 为真
- [x] 测试:`"a\n\nb"` 逐行导出占三行,中间那格是空的
- [x] 测试:逐行导出的单元格 `wrap_text` 为假
- [x] 测试:迁移后既有文字 Block 的 `split_lines` 是 `True`
- [x] `make check` 与 `make test` 通过

