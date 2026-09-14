# 01: 文字 Block 转为表格

**Status:** resolved

**Blocked by:** 无

**What to build:** `POST .../blocks/<id>/as-table`,以及 `BlockCard` 上对应的按钮。

**后端**

- 端口和既有的 `as-text` **同形**(`turn_block_into_text` 就在隔壁,照着写)。只接受 `kind == "text"` 的 Block,别的 kind 是 422。
- 用 `tables.table_in(block.text)` 切。**`html` 传 `None`** —— text Block 手里只有纯文字,没有第二种 flavor。
- 切不出来(返回 `None`)时给一个**说得出原因**的拒绝,走 `errors.py` 既有那套 code + 中文消息,和 `EmptyBlockText` / `EmptyTable` 一个路子。
- 切得出来时:`kind = TABLE`,`rows = 切出来的`,`has_header = len(rows) > 1`,`table_source = block.text`(当下这段文字,好让 `as-text` 还能原样退回来),`text = ""`,`split_lines` 回到默认。
- Block 还是同一个 Block:`id`、`label`、`order` 都不动。

**前端**

- 按钮只在 `block.kind === "text"` **且** `block.text` 含 `\t` 且含 `\n` 时才画出来。这条判断和 `clipboard.ts` 的 `carriesTable` 是同一条规则的第三个副本 —— **把它抽出来共用**,别再抄一遍(`carriesTable` 自己的注释就写着粗筛和后端判别必须认同一套标记)。
- 一段普通日志上不该出现一颗注定失败的按钮,这和「拆行 / 合并」只在含换行时才出现是同一条做法。
- 按钮画出来了**仍然可能被拒绝**(判断的权威在服务端),被拒时把消息显示出来,Block 保持原样。
- 位置:和 `kind === "table"` 那组工具条按钮对称,放在文字 Block 的「编辑」旁边。

**别动**:`add_pasted_block` 的判别顺序、`as-text` 的既有行为、表格的删行删列改单元格(以及「刻意没有加行加列」那条 —— 这次也不许出现能凭空造出一行的路径)。

- [x] 一个表格「改为文字」,再「转为表格」→ 行列和原来一致
- [x] 一段从来没被认出来过的 TSV 日志,点「转为表格」变成表格
- [x] 改为文字后**编辑过**再转回表格 → 按编辑后的文字切,不是按原来的
- [x] 一段没有制表符的日志上**看不到这颗按钮**
- [x] 含制表符但切不出表格的文字(比如只有一行且不以换行结尾)→ 按钮在,点了给出说得清的拒绝,Block 保持原样
- [x] 转成表格后 `label` 和在用例里的位置都没变
- [x] 单行的转换结果 `has_header` 是 `false`(既有规则)
- [x] 对 image Block 调这个端点是 422
- [x] 来回改五次,内容不劣化
- [x] 后端测试补在 `test_evidence_table_block_api.py`;`make test` 通过
