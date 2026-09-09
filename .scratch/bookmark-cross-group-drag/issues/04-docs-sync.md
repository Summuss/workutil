# 04: 文档与手动清单同步

**What to build:** 核对 `docs/requirements.md` F3、`docs/design.md` F3 里先行写好的描述与实际实现一致,并补 `docs/running.md` 的手动清单。

`DragOverlay` 改变了**全部五处**已有拖拽的观感,清单里现有的拖拽复核条目要跟着改口径 —— 现在的期望是「跟随光标的浮层 + 原位占位空槽」,不是原来的「原地半透明」。

**Blocked by:** 03

**Status:** resolved

- [x] 核对 `design.md` F3 里跨组拖拽那条与实际接口形状一致
- [x] `running.md` 现有的五处拖拽复核条目改口径为 `DragOverlay` 的表现
- [x] `running.md` 补:把散装书签拖进一个组,落在松手的位置
- [x] `running.md` 补:把书签从组里拖回散装区
- [x] `running.md` 补:在两个组之间拖书签,两边顺序都正确
- [x] `running.md` 补:新建一个空组,直接拖一条书签进去
- [x] `running.md` 补:跨组拖完 `F5`,结果不变
- [x] `running.md` 补:拖动时元素在滚动区边缘不被裁剪
- [x] `.scratch/drag-reorder/issues/03-bookmark-drag-reorder.md` 里「跨组拖拽确实不可行」那条已被本轮反转,补一行指向本目录的说明(不重写历史)
- [x] 若实现中对 spec 做了偏离,在 `spec.md` 里改掉
