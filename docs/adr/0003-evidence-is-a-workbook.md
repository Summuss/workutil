# Evidence 是一个工作簿,不是一份记录

看 requirements.md 的第一印象是「一份 evidence = 一个有序的内容列表」,做成两层(Evidence → 条目)最省事。实际的交付物**不是这个形状**:一个 evidence 文件对应**一批测试用例**,每个用例占一个 sheet,sheet 名是用例编号(`1`、`2`、`2~5`,不一定是数字),用例内部才是有序的内容。少掉中间这一层,一个用例就只能是一个文件,而实际交付的是一个文件。

因此模型是三层:**Evidence → Case → Block**(见 CONTEXT.md)。

## Consequences

- 「步骤编号」这个概念从模型里删掉了。Block 之间是**分节**关系(事前準備の DB データ / 画面 / ログ / DB 更新後の結果),不是 1→2→3 的步骤;编号只会在插入一节时全部错位。Block 用可选的 `label` 当小标题。
- 一个 sheet 只有一套列宽,所以**同一个 Case 里的多个表格共用列宽**。这是 Excel 的形状,不是实现偷懒,不要试图「修」它。
- 三层意味着前端有三级导航(Evidence 列表 → 某份 Evidence → Case 标签),这是 M2 引入 react-router 的直接原因。
