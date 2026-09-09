# 01: 后端复制用例端点

**What to build:** `POST /api/evidence/{evidence_id}/cases/{case_id}/duplicate`,请求体为空(名字由服务端生成),返回**整个 cases 列表**(插入会改变后面所有 `order`,只回新用例会让前端拿到过期的序号)以及新用例的 id。

**图片必须连文件一起复制成新名字 —— 这是本 ticket 唯一会造成数据损失的地方。** Evidence 的图片引用是结构化的、不做引用计数(design.md §5),`delete_case` 会按 `image_name` 逐个删文件。副本若共享同一个 `image_name`,删掉副本就会**静默删掉原用例的截图**。复制时要在同一个 evidence 的图片目录里把文件另存为新名字,沿用 `core/images.py` 现有的命名机制。

**命名**:`原名 (2)`,撞了继续 `(3)`、`(4)`…,大小写折叠后比较(和 `_refuse_duplicate_name` 同一套规则)。**31 字符上限要处理**:`原名 + 后缀` 超长时**截断原名**以容纳后缀,而不是拒绝复制。生成的名字自己也要过一遍 `validate_case_name`。

**位置**:插在原用例的紧后面,后面所有用例的 `order` 顺延且连续。

`rows` 是 JSON 列、按标识跟踪,复制时要**赋一个全新的列表**,不能把原对象挂到新行上(`models.py` 里那条注释说的就是这个坑)。

**Blocked by:** 无

**Status:** ready-for-agent

- [ ] `POST .../cases/{case_id}/duplicate` 端点,返回整个 cases 列表 + 新用例 id
- [ ] 复制所有 Block:`kind`、`label`、`text`、`order` 原样;`id` 与时间戳是新的
- [ ] 表格 Block 的 `rows` 与 `has_header` 复制,`rows` 是**全新的列表对象**
- [ ] 图片文件在磁盘上另存为新名字,新 Block 指向新 `image_name`
- [ ] 命名:`1` → `1 (2)`,连续复制得到 `(3)`;大小写折叠比较
- [ ] 命名:超过 31 字符时截断原名,总长 ≤ 31,且不与任何现有用例重名
- [ ] 新用例插在原用例紧后面,全部 `order` 连续
- [ ] 原用例不存在 / 不属于这份 evidence → 404
- [ ] 测试:副本的 `image_name` 与原件**不同**,两个文件都在磁盘上
- [ ] 测试:**删掉副本之后,原用例的图片文件仍在** —— 这条是这个功能的核心风险
- [ ] 测试:导出 Excel,原用例与副本是两个内容相同的 sheet,图片都在
- [ ] `make check` 通过
