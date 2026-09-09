# 05: 同步文档,记录「不做拖拽」决定的反转

**What to build:** 01-04 落地后,把散落在多处的「不做拖拽」说明改成实际的新决定,并说明为什么这次反转是有理由的(dnd-kit 自带键盘拖拽,当初放弃拖拽最主要的可访问性成本已经不成立)。

**Blocked by:** 01, 02, 03, 04

**Status:** resolved

- [x] `docs/design.md`(Evidence 排序段落,原文「交互是上下移动 + 置顶/置底按钮,不做拖拽」)改写为新决定 + 反转理由
- [x] `.scratch/evidence/spec.md`(Implementation Decisions 里的排序说明 + Out of Scope 表里的「拖拽排序」行)同步更新
- [x] `.scratch/bookmark/spec.md`(同上两处)同步更新
- [x] `.scratch/todo/spec.md`(排序说明段落 + 接口面表格里的 `move` 端点请求体)同步更新
- [x] 在 `.scratch/evidence/issues/04-text-block.md`、`.scratch/bookmark/issues/03-groups.md`、`.scratch/todo/issues/02-manual-ordering.md` 这三个已关闭的历史 ticket 底部各加一条简短说明,指向本目录,**不改动它们原本的验收清单**(它们是历史记录)
- [x] 全文搜索一遍「不做拖拽」/「不值一个依赖」确认没有漏改的地方
