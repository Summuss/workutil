# 04: 从 memo 转出 Todo

**What to build:** memo 卡片上的「转 Todo」按钮、`/memo/:id` 这个新路由,以及 Todo 上指回原 memo 的链接。

**这是 M3 里唯一会碰 memo 的地方,而它有两条不能破的约束。**

**一、`/` 不能变。** 打开工具仍然直接是 memo 输入框、光标已在里面(requirements.md §4 F1)。新路由只在从别处指回来时才存在。这是 M2 的 ticket 01 就立下的规矩。

**二、后端 memo 一行不动。** `source_memo_id` **只存 id,不建外键约束**,取不到就不显示链接;memo 那边**不显示**「已转成 Todo」。真 FK 要么让 memo 的删除路径去关心 todo 表、要么依赖 SQLite 的 `PRAGMA foreign_keys`;memo 侧的标记则要求 memo 的查询去 join todo —— 三条都是让新功能反向污染旧功能,而「新增一个功能不应改动既有功能」是本项目第一约束(requirements.md §5)。前端 `features/memo` 单向依赖 `features/todo` 的 api 是知情的一处例外,**反向永远不许**。

**回溯目标必须是 `/memo/:id`,不能是「滚到列表里那一条」。** memo 列表有 `RECENT_MEMO_LIMIT`,三个月前那条原 memo 很可能根本不在列表里 —— 而三个月前正是最需要回溯的时候。`/memo/:id` 只显示那一条(渲染态、可编辑),顶部一个「回到全部」。

**标题:弹一个输入框,预填 memo 正文首行(`firstLine.ts` 已有),当场可改。**

- 不直接拿首行:它经常不是待办本身(「昨天那个报错:」下面第三行才是要做的事),那会稳定地产出需要二次编辑的垃圾标题
- 不用选区:design.md §6 F1 记着「点正文进编辑会吃掉选区」的教训,选区在按钮被按下那一刻是否还在,取决于浏览器和用户怎么点,不该拿它当输入

按钮在 **memo 卡片的工具条**上 —— 场景是「写着写着发现这是个待办」,放到 Todo 页里去翻反而更慢。

**Blocked by:** 01

**Status:** done

- [x] `todos.source_memo_id`(可空、**不建 FK**)+ 迁移;`POST /api/todos` 可带
- [x] 新路由 `/memo/:id`:只显示那一条 memo,渲染态可编辑,顶部「回到全部」
- [x] memo 卡片工具条上的「转 Todo」:弹窗预填首行、可改、确认后生成
- [x] Todo 上显示回溯链接,点击进入 `/memo/:id`
- [x] **原 memo 已删时,Todo 仍正常显示,只是没有链接**
- [x] 打开 `/` 仍然直接是 memo 输入框、光标已在里面
- [x] 后端 `modules/memo/` **零改动**(改了就说明走错路了)
- [x] 主接缝测试:`source_memo_id` 指向一条已删 memo 的 todo 仍能正常列出
- [x] `make check` 与 `pnpm build` 通过
