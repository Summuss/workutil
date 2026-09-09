# Todo 的说明不是一条 Memo

Todo 原本只有一个标题。「这件事到底是什么」没地方写,于是有了 **memo 转 Todo**:memo 写着写着发现是个待办,一键转出,并保留一条回溯链接指回原 memo。requirements.md §4 F2 把它写成「与 F1 打通」,`.scratch/todo/issues/04-from-memo.md` 为它写了整整一页约束。

**现在 Todo 有了自己的说明,那条转换的存在理由就消失了。** 它不是不好用 —— 是当初要带过去的本来就是「那段描述」,而不是「那条 memo」;绕经 memo 只是因为 Todo 那边没有地方放字。

但这带来一个新问题:说明和 Memo 的正文**形态一模一样**(都是人写的一段字,都走 Markdown 渲染)。既然长得一样,为什么不干脆让 Todo 挂一条 Memo?

**因为它们的生命周期不同。** Memo 是一条**记录**:有自己的创建时间,能被搜索捞回,能置顶,删不删由你单独决定 —— 它独立存在,不依附于任何东西。说明是**一件事的附注**:没有自己的时间戳,不参与搜索,不能置顶,那条 Todo 一删它就跟着没了。形态相同是巧合(都是字),概念不同是本质。这和 [ADR-0001](./0001-memo-and-evidence-are-separate-concepts.md) 给 Memo / Evidence 划的是同一条线:**共享机制,不共享概念。**

## Consequences

- `todos.description` 是 todos 表上一个普通的 `Text` 列(default `""`),**不是指向 memos 的外键,也不是一张关联表**。
- **说明不参与搜索。** 搜索是 Memo 的能力(requirements.md §4 F1「事后能靠关键词快速找回」),Todo 靠的是「就在眼前的一份短列表」。哪天说明真的需要被独立搜索,那说明它其实是一条 Memo —— 那时该重开这条决定,而不是给 Todo 加搜索。
- **说明不支持图片。** 图片链路(`core/images.py`)是共享的,复用成本不高,但一旦说明能装截图,它和 Memo 就只剩「有没有勾选框」这一个区别了。截图属于 Evidence(那是交付材料)或 Memo(那是记录)。
- **Markdown 渲染器从 `features/memo/` 提到 `shared/`**,连同它那条「禁用 raw HTML」的安全线与守卫测试。这是「共享机制」在前端的落点,同时避免 `features/todo` 反向依赖 `features/memo` —— `.scratch/todo/issues/04-from-memo.md` 立过「反向永远不许」的规矩,拆掉正向依赖时不该留下新债。
- **`todos.source_memo_id` 被 drop。** 迁移里先把还活着的链接接住:凡 `source_memo_id` 非空且那条 memo 仍在的,往新的 `description` 里追加一行 `[原 memo](/memo/N)` —— 线索留在说明里,而不是随列一起消失。
- **`/memo/:id`(`SingleMemoPage`)保留。** 它是「一条 memo 的固定地址」,上面那条迁移生成的链接就指向它。拆掉徽章之后它一度没有 UI 入口,这条迁移把入口还了回来。
- CONTEXT.md 新增「说明(Description)」词条,Todo 词条里「可以由一条 Memo 转出」那句作废;requirements.md §4 F2 的「与 F1 打通」整段随之改写。
