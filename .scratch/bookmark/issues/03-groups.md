# 03: 组与排序

**What to build:** Group 的表与增删改、把书签移进移出组、组内排序与组自身排序。`GET /api/bookmarks` 从此返回「各组 + 散装」。

**一个 Bookmark 属于零或一个 Group。** 不是多对多、不是标签。同一个文件要出现在两个组里,就登记两条书签 —— 它们各有各的名字和各自的位置,而多对多模型没地方放这两套名字(ADR-0006)。散装书签是合法的,不要强制建组。

**删掉一个 Group,成员变成散装、不跟着删。** 登记一个入口和编排一次开机要开哪批是两件事,删编排不该带走登记;而误删的补救是回文件管理器里重新翻出那些路径 —— 正是这个功能存在的理由所要消灭的动作。

排序**直接复用 evidence 的 `_reordered` / `Move`**(上下移动 + 置顶 / 置底,**不做拖拽**)。组内书签排 `bookmark.order`,组自身排 `group.order`(「每日必开」应该能置顶)。删除后要**重新编号**,和 evidence 一样,别留空洞。

**Blocked by:** 02

**Status:** done

- [x] 迁移:`bookmark_groups` 表 + `bookmarks.group_id`(可空)
- [x] `POST /api/bookmark-groups` / `PATCH {id}`(改名)/ `DELETE {id}` / `POST {id}/move`
- [x] `POST /api/bookmarks/{id}/move`(组内上下 / 置顶 / 置底)
- [x] `PATCH /api/bookmarks/{id}` 能改 `group_id`(移进组、移出成散装)
- [x] `GET /api/bookmarks` 返回各组(按 `group.order`)+ 散装
- [x] **删组之后成员还在、`group_id` 变空**
- [x] 前端:建组 / 改名 / 删组、把书签移进移出、两级排序
- [x] HTTP 主接缝测试;`make check` 与 `pnpm build` 通过

---

> **后续更新 (2026-09):** 排序交互已由四个按钮改为拖拽把手 + 置顶/置底，接口扩展支持绝对位置 `to: int`。详见 `.scratch/drag-reorder/`。
