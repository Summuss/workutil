# 02: 手工排序

**What to build:** Todo 的 `order` 字段与移动接口,**直接复用 evidence 的 `_reordered` / `Move`**(上下移动 + 置顶 / 置底,不做拖拽)。

**排序是手工的,因为优先级只有人知道。** 不要改成按创建时间、也不要按截止日期(见 03:`due_date` 不参与排序)。

**完成时 `order` 原样不动,撤销就回到原来的位置。** 这一条是本 ticket 真正要守住的东西:若改成置底,一次误点「完成」就永久打乱了手工排好的优先级,而手工排序的全部意义就在那个顺序里。删除后重新编号,和 evidence 一样,别留空洞。

**Blocked by:** 01

**Status:** done

- [x] `todos.order` 字段 + 迁移;新建的排在末尾
- [x] `POST /api/todos/{id}/move` `{to: up|down|top|bottom}`,复用 `_reordered`
- [x] 未完成列表按 `order` 返回
- [x] `complete` / `reopen` **不修改 `order`**
- [x] 前端:每条上的上下移动 + 置顶 / 置底
- [x] 主接缝测试:**完成再撤销,todo 回到原来的位置**
- [x] `make check` 与 `pnpm build` 通过

---

> **后续更新 (2026-09):** 排序交互已由四个按钮改为拖拽把手 + 置顶/置底，接口扩展支持绝对位置 `to: int`。详见 `.scratch/drag-reorder/`。
