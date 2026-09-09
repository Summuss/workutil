# 02: Todo 列表改为拖拽排序,并搭好前端拖拽基础设施

**What to build:** 引入 dnd-kit(`@dnd-kit/core` + `@dnd-kit/sortable`,项目目前零拖拽依赖),先在 Todo 列表上落地 —— 这是五个改造目标里的第一个,顺带把后面 Bookmark、Evidence 要复用的拖拽基础设施(可复用的 sortable 包装、拖拽把手图标)搭起来。

去掉 `TodoItem` 上的「上/下」按钮,保留「置顶/置底」。每行加一个专门的拖拽把手图标(新增到 `shared/icons.tsx`,沿用现有 feather 描边风格),只有按住把手才能拖动 —— `TodoItem` 这一行还有 checkbox、编辑、删除、「从 memo 转入」链接等其他可点击元素,整行可拖会和这些冲突。

启用 dnd-kit 的键盘 sensor(空格拾起、方向键移动、空格放下),这是选 dnd-kit 而不是手写实现的主要理由。

拖拽范围与现有按钮完全一致:仍是同列表内排序;仍只有未完成且列表长度 > 1 的项可排序(与现有按钮的显示条件一致)。松手时用 ticket 01 的绝对位置接口发一次请求;发请求前本地先乐观重排,请求失败则回滚并提示错误(沿用现有的错误 code + 多语言展示机制)。

**Blocked by:** 01

**Status:** resolved

- [x] 引入 `@dnd-kit/core` + `@dnd-kit/sortable`
- [x] `shared/icons.tsx` 新增拖拽把手图标(feather 风格)
- [x] 可复用的 sortable 列表包装(供 03、04 复用),而不是把 dnd-kit 接线逻辑焊死在 Todo 组件里
- [x] `TodoItem`:去掉「上/下」按钮,保留「置顶/置底」;新增拖拽把手,只有把手可拖
- [x] 键盘拖拽可用(Tab 到把手 → 空格拾起 → 方向键移动 → 空格放下)
- [x] 拖拽范围限制:仅未完成项参与排序,与现有按钮显示条件一致
- [x] 松手时调用 ticket 01 的绝对位置接口;本地乐观更新,失败时回滚并用既有的多语言错误展示机制提示
- [x] `pnpm build`/`tsc` 通过;手动跑 `/run` 验证鼠标拖拽与键盘拖拽
