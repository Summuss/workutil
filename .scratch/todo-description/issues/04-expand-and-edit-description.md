# 04: Todo 展开看说明,编辑表单里改说明

**What to build:** `TodoItem` 的展开态,以及编辑表单里的说明输入框。

**展开:**

- **有说明才显示展开箭头**,并在行上给一个小标记。没说明的待办是多数,一列灰箭头全是噪音(User Story 3)。
- 展开后用 `shared/Markdown`(票 02)渲染说明,代码块等宽带高亮 —— 和 memo 正文同一个渲染器,同一条「禁用 raw HTML」的安全线。
- 展开状态按 todo id 持久化到 `localStorage`,**照抄 `MemoList` 的写法**:`typeof window !== "undefined" && window.localStorage` 判断 + try/catch,不可用时静默降级为「不记忆」,不报错不崩溃。
- **已完成的待办也能展开、只读** —— 和现有「已完成不显示编辑按钮」一致(User Story 5)。
- **展开不影响拖拽。** `canReorder` 现在是 `!isCompleted && !editing && onMove !== undefined && count > 1`,展开**不进这个判断** —— 卡片变高但把手还在顶部行。

**编辑:**

- 说明在**现有的编辑表单**里改:标题 + 截止日期 + 说明,一次保存(User Story 6)。不另开一个编辑态 —— 那会让「改标题」和「改说明」变成两个动作。
- 说明框是纯文本 `textarea`,**不做所见即所得**(和 memo 编辑区同一个理由)。
- 没有说明的待办,说明框照常出现在编辑表单里,是补写说明的唯一入口。

**别做的事:** 说明不参与搜索、不能置顶、不支持图片粘贴。这三条不是「以后再说」,是 [ADR-0012](../../../docs/adr/0012-a-todo-description-is-not-a-memo.md) 划的界 —— 越过任何一条,说明就变成第二个 Memo 了。

**Blocked by:** 01, 02

**Status:** ready-for-agent

- [ ] 有说明的待办显示展开箭头 + 一个小标记;**没说明的不显示**,行高不变
- [ ] 展开后用 `shared/Markdown` 渲染说明,代码块带高亮
- [ ] 说明里的 `<script>` 原样显示为文字,不执行
- [ ] 展开状态写入 / 读回 `localStorage`,按 id 记忆;`localStorage` 不可用时静默降级
- [ ] 已完成的待办可展开、**只读**(无编辑入口)
- [ ] 编辑表单里加说明 `textarea`,与标题、截止日期一次保存
- [ ] 清空说明后保存,展开箭头随之消失
- [ ] 展开一条待办后仍能拖拽排序,把手位置正常
- [ ] `todo.description_label` / `todo.description_placeholder` / `todo.expand` / `todo.collapse` 等文案中日双份,key 对齐测试通过
- [ ] `pnpm build` / `tsc` 通过;手动验证展开、刷新保持、已完成只读三条
