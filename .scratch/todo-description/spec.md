# Spec: Todo 说明(并作废 memo 转 Todo)

Status: ready-for-agent

## Problem Statement

一行标题经常说不清那件事到底是什么 —— 报错长什么样、要动哪个文件、上次卡在哪一步。这些以前没地方写。

**曾经有过一个绕道的答案**:memo 写着写着发现是个待办,一键转成 Todo,并保留一条回溯链接指回原 memo(requirements.md §4 F2 的「与 F1 打通」)。它能用,但它解决的是另一个问题 —— 当初要带过去的本来就是**那段描述**,而不是那条 memo;绕经 memo 只是因为 Todo 那边没有地方放字。

## Solution

给 Todo 加一个可选的**说明**:一段文字,和 memo 正文一样走 Markdown 渲染。列表里默认收起,**有说明的才显示展开箭头**,展开后看到全文。

memo 转 Todo 随之作废:按钮、模态、徽章、`source_memo_id` 列全部拆掉。

## Domain Model

**这会改 `CONTEXT.md`,已经改了。** Todo 词条里「可以由一条 Memo 转出」那句作废,新增「说明(Description)」词条,底部补一条划界引文。

要守住的界限是:**说明不是一条 Memo**。形态相同(都是人写的一段字、都走 Markdown),概念不同 —— Memo 是一条**记录**,有自己的创建时间、能被搜索捞回、能置顶、删不删单独决定;说明是**一件事的附注**,没有自己的时间戳、不参与搜索、不能置顶,Todo 一删它就没了。

这和 ADR-0001 给 Memo / Evidence 划的是同一条线:共享机制,不共享概念。详见 [ADR-0012](../../docs/adr/0012-a-todo-description-is-not-a-memo.md)。

## User Stories

1. 作为使用者,我希望在待办上写清楚「这件事到底是什么」,不用为此另开一条 memo。
2. 作为使用者,我希望说明里贴命令行和报错时好读 —— 和 memo 正文一样的呈现。
3. 作为使用者,我希望**一眼看出哪几条有说明**,没说明的不占额外的视觉位置。
4. 作为使用者,我希望展开一条看说明之后刷新页面,它还是展开的。
5. 作为使用者,我希望已完成的待办也能展开看说明(只读),回顾「上周那件事当时是怎么回事」。
6. 作为使用者,我希望改标题、改截止日期、改说明是**一次编辑**,不是两个入口。
7. 作为使用者,我希望升级之后,原先那些从 memo 转出来的待办**不会丢掉线索** —— 还能找回原 memo。

## Implementation Decisions

### 数据与接口

- `todos.description: str`(`Text`,default `""`),**不是外键、不是关联表**。
- **同一条迁移里做三件事,顺序不能换**:①加 `description` 列;②凡 `source_memo_id` 非空**且那条 memo 仍在**的,往 `description` 追加一行 `[原 memo](/memo/N)`;③drop `source_memo_id`。第 ② 步是整个 spec 里唯一不可逆的地方 —— 顺序错了线索就没了。
- `TodoUpdate.description: str | None` —— `None` = 不改,`""` = 清空。**不用** `due_date` 那套 `model_fields_set` + `update_due_date` 的 sentinel:`due_date` 需要它是因为 `null` 本身就是合法目标值,而空字符串和「没传」在这里天然可分。
- `GET /api/todos` **带说明全文回来**。对照组是 evidence 的 Block(按 Case 单独读,因为可能挂着一整天的截图)—— 说明是纯文本、没有图片,体积有上界,带回来换到的是「展开即刻可见」。
- **说明不参与搜索、不能置顶、没有自己的时间戳。** 哪天它真需要被独立搜索,那说明它其实是一条 Memo,该重开 ADR-0012 而不是给 Todo 加搜索。
- **说明不支持图片。** 图片链路(`core/images.py`)是共享的、复用成本不高,但一旦说明能装截图,它和 Memo 就只剩「有没有勾选框」这一个区别。
- 拆除 `source_memo_id` 的同时,`router.py` 里那套 `get_existing_memo_ids` + `_to_read(todo, valid_memo_ids)` 的过滤一起删,`_to_read` 退回一行 `TodoRead.model_validate`。

### 前端

- **`MemoMarkdown.tsx` 提到 `shared/Markdown.tsx`**,连同 `MemoMarkdown.test.tsx` 那条「禁用 raw HTML」的守卫。**`features/todo` 不许 import `features/memo`** —— 旧的正向依赖(`features/memo` → `features/todo` 的 api)随转换一起拆掉了,不该在拆的同时留下反向的新债。
- **有说明才显示展开箭头**,并在行上给一个小标记。没说明的是多数,一列灰箭头全是噪音。
- 展开状态按 id 持久化到 `localStorage`,照抄 `MemoList` 的写法(`typeof window !== "undefined"` 判断 + try/catch,不可用时静默降级)。
- 已完成的 Todo **可展开、只读**,和现有「已完成不显示编辑按钮」一致。
- 说明在**现有的编辑表单**里改(标题 + 截止日期 + 说明一次保存),不另开一个编辑态。表单里的说明框是纯文本 `textarea`,不做所见即所得。
- 展开**不影响拖拽**:`canReorder` 现在的条件是 `!isCompleted && !editing && ...`,展开不进这个判断 —— 展开的卡片变高但把手还在顶部行。
- 文案两种语言都要:`todo.description_label`、`todo.description_placeholder`、`todo.expand`、`todo.collapse`、`todo.has_description`。删掉的 `memo.to_todo` 等 key 两边一起删(key 对齐测试会看着)。

## Testing Decisions

| 位置 | 测? | 理由 |
| --- | --- | --- |
| HTTP API:说明的增删改 | ✅ 主接缝 | `None` 不改 / `""` 清空 这两条语义容易写反 |
| HTTP API:列表带说明全文 | ✅ 主接缝 | |
| **迁移:旧链接被接住** | ✅ **重点** | 造三条 todo(指向存在的 memo / 指向已删的 memo / `source_memo_id` 为空),跑迁移,断言只有第一条的说明里多了链接。这是唯一不可逆的一步 |
| `shared/Markdown` 的 raw HTML 守卫 | ✅ 搬家后仍然绿 | 全项目唯一破例的前端测试,换目录不能把它弄丢 |
| 展开 / 折叠 / localStorage | ❌ | 沿用一贯做法,手动跑 |

## Out of Scope

| 项目 | 说明 |
| --- | --- |
| 说明里贴图片 | 见上,那会让 Todo 变成第二个 Memo |
| 说明参与搜索 | 同上。真需要就是 ADR-0012 该重开的信号 |
| 保留 memo→Todo 转换 | 作废。Todo 有了说明之后它没有存在理由 |
| 反过来「Todo 转 Memo」 | 没有这个场景 |
| `/memo/:id` 一起删 | **保留**。它是一条 memo 的固定地址,而迁移生成的链接正指向它 |

## Further Notes

### `firstLine.ts` 不要删

它是当初为「转 Todo 时预填 memo 首行」写的,但折叠态 memo 的首行显示也在用它(`MemoItem.tsx`)。拆转换的时候容易顺手带走。

### 为什么 `/memo/:id` 值得留

拆掉徽章链接之后,`/memo/:id` 在应用内一度**没有任何入口**(全前端只有 `TodoItem.tsx:264` 一处链接过去)。留着它的理由不是「以后可能有用」,而是迁移那一步会往说明里写 `[原 memo](/memo/N)` —— 入口当场就回来了。这两个决定是扣在一起的,不要只做一半。
