# 03: Evidence 与 Case 的骨架

**What to build:** 三层模型的上面两层。Evidence(一个 xlsx 文件)和 Case(一个测试用例 = 一个 sheet)的建、删、改名、排序,以及 Evidence 列表页和 Case 标签栏。

**sheet 名的合法性在这里就要拦住**,不能留到导出时清洗 —— sheet 名是交付内容的一部分,导出时悄悄改名等于交给使用者一个他没检查过的文件。约束:非空、≤31 字符、不含 `: \ / ? * [ ]`、同一 Evidence 内不重名。注意 **openpyxl 只对非法字符抛 `ValueError`,超长仅发 `UserWarning` 并原样写进文件**(实测 3.1.5),长度这一关它不兜底,必须自己校验。`2~5` 是合法的。

Evidence 列表创建时间倒序、固定上限,**不做搜索**:ADR-0001 把「靠搜索捞回」明确划给了 Memo。

**Blocked by:** 01

**Status:** done

- [x] `evidence` 与 `evidence_case` 两张表 + Alembic 迁移
- [x] Evidence:建 / 改名 / 删 / 列表(创建时间倒序,固定上限,列表里显示 Case 数)
- [x] Case:建 / 改名 / 删 / 调整先后(上下移动 + 置顶 / 置底)
- [x] sheet 名校验:空、>31 字符、含 `: \ / ? * [ ]`、同 Evidence 内重名 —— 全部在录入接口被拒
- [x] `2~5` 这样的名字能正常保存
- [x] 删 Evidence 时它的图片目录 `images/evidence/<id>/` 一并删掉,**删不掉文件不算失败**
- [x] 前端:`/evidence` 列表页、`/evidence/:id` 详情页(Case 标签栏,内容区先留空)
- [x] HTTP 主接缝测试覆盖上述增删改与全部校验分支
