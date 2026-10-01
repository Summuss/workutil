# 02: Block 的备注:卡片上可写可看,灯箱上可看,不导出

**Status:** ready-for-agent

**Blocked by:** 01

**What to build:** 三种 Block 都可以带一条单行的备注。备注写给记录者自己看,不导出。在卡片上写和看,图片 Block 的备注在灯箱里也看得到。理由见 [spec](../spec.md)。

### 后端

- `EvidenceBlock` 加一列 `note`:`Text`,可空。写 Alembic 迁移,已有的行都是 `NULL`。
- `PUT .../blocks/<id>/note`,请求体是 `{"note": ...}`。它和 `/label` 同形,两者都属于每一种 kind。清理规则复用小标题的:去掉首尾空白,空串就是 `None`。
- `BlockRead` 带上 `note`,三种 kind 都带。
- `duplicate_case` 要显式复制 `note`。那里是一个字段一个字段地抄,漏抄的话,复制出来的用例上的备注会静静地消失。
- **导出不读它。** 加一条测试守着这一点:给 Block 写一条备注再导出,遍历工作簿里所有单元格,找不到这段文字。
- 测试走 HTTP 主接缝:三种 kind 都能写、能读回;空白等于清空;复制用例后备注一致,改副本的备注不影响原用例。

### 前端

- `Block` 类型加 `note: string | null`,`api.ts` 加 `setBlockNote`,`CaseBlocks` 加 `handleNote`,照着 `handleLabel` 写。
- `BlockCard`:
  - 没有备注、也没在编辑时:工具条上加一颗「备注」(`TOOL_BUTTON`),点了在标题行下面打开 `InlineEdit`。
  - 有备注时:标题行下面一行显示备注,用提醒色(`--warn` / `--warn-tint`)。点它进入 `InlineEdit`;`title` 说明「只在工具里看,不会导出」。工具条上那颗按钮这时不显示,改备注的入口就是这一行。
  - `Enter` 存,`Esc` 放弃;存失败时输入框留着,和小标题一样。
- `shared/Lightbox` 加**可选**的 `note` prop。有值时,底部居中显示一条:样式和顶部说明一样(半透明黑底、白字、圆角),前面加一个提醒色的「备注」字样。设 `pointer-events-none`,框选模式下在它下面拖动照样能画框。最大宽度 70vw,字多就换行。memo 不传。
- `BlockOutlineRow` 不显示备注。
- 新文案出中日两份。

### 文档

- `CONTEXT.md` 加「备注」一条:Block 上的一行字,写给记录者自己看,**不导出**。它和小标题的区别只有一个:小标题是交付物的一部分,备注不是。_Avoid_: 注释、批注 / Comment(Excel 里另有其物)、Memo(另一个概念)、说明(Todo 的)。
- `docs/requirements.md` F5 加一条需求和验收要点。
- `docs/design.md` §6 F5:`/note` 和 `/label` 同形;不导出;`duplicate_case` 复制它;没有草稿。
- `docs/running.md`:文字 Block、图片 Block 两节和 Excel 导出一节补手测步骤。

### 验收

- [ ] 给一个文字 Block 点「备注」,填「待确认」回车:标题行下面出现这一行,颜色和正文不同
- [ ] 点这行改成别的、回车,改好了;清空回车,这行没了,「备注」按钮回来了
- [ ] `Esc` 放弃修改,备注还是原来的
- [ ] 图片和表格 Block 也能加备注
- [ ] 给一张图加了备注,开灯箱,底部能看到它;按 `→` 翻到没有备注的图,底部那条消失
- [ ] 框选模式下,在备注那条下面拖动,照样能画出框
- [ ] 刷新之后备注都在
- [ ] 复制用例,新用例同一段上有同样的备注;改副本的备注,原用例不变
- [ ] 导出 Excel,在里面搜备注的文字,搜不到
- [ ] 大纲里看不到备注
- [ ] 后端测试绿;`pnpm build` / `tsc` 通过;中日文案的 key 对齐测试通过

## Comments
