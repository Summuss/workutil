# 表格是一等内容类型,不是文字的一种

Evidence 里有三种内容:文字、图片、表格。表格来自 DB 客户端复制出来的结果集(事前準備の DB データ、DB 更新後の結果),它**必须以行列结构存下来**,不能当成一段文字。

这一条决定了 Evidence **不能复用 Memo 的 Markdown 正文模型**。Markdown 里图文混排是可行的,表格也能写,但 openpyxl 的图片是浮动锚定在单元格上的、不在文字流里 —— 「一个格子里文字和图片按 Markdown 顺序混排」在 Excel 里根本做不到。要导出成 Excel,内容就必须是**类型明确的块序列**,而不是一段需要解析的富文本。

粘贴进来的那一刻是唯一还知道单元格边界的时候(DB 的文本字段本身就可能含制表符和换行),所以解析在粘贴时完成并定型为二维数组,不存原始 TSV 事后再切。

## Consequences

- Block 有 `kind`(`text` / `image` / `table`)。Log 归进 `text`,不单列一类。
- 表格存 `rows: string[][]` 加一个 `has_header` 标志。**`has_header` 不能靠猜**:IDEA 的 database 工具复制时带不带表头,取决于 Settings → Tools → CSV Formats → TSV 里的「First row is header」,工具这边无从判断第一行是列名还是数据。默认 `true`,UI 上一键可翻转。
- 导出时所有单元格统一写成 `@` 文本格式。DB 里的 `007`、`2024-01-01`、18 位 ID 交给 Excel 自动识别会分别变成 `7`、日期序列号、科学计数法,而 evidence 的全部意义就是「我看到的就是这个值」。代价是 Excel 会挂「以文本形式存储的数字」绿色三角 —— 接受它;openpyxl 3.1.5 的 `IgnoredErrors` 类没有接到 worksheet 上,压掉它要拆 xlsx 的 zip 手改 XML,不值得。
