# workutil

一个自用的本地开发效率工具,把日常开发中高频而琐碎的动作收进同一个地方。

## Language

**Memo**:
随手记下的一则琐碎信息,可以包含文字和图片。一次保存产生一条 Memo,粒度由记录者当场决定。
_Avoid_: Note, 笔记, 碎片信息

**置顶(Pinned)**:
Memo 上的一个比特:「这条现在常用」。置顶的 Memo 排在列表最前,彼此按置顶时间倒序。
它**不是分类** —— 没有维度、没有名字、发生在记录之后、随手可开可关,因此不构成录入负担;
这正是它与被推迟的「标签归类」的分界线(见 [ADR-0008](./docs/adr/0008-memo-can-be-pinned-but-not-categorised.md))。
只有 Memo 有这个概念:Todo、Bookmark、Case、Block 本来就有显式顺序,想要靠前直接拖过去。
_Avoid_: 收藏, 标签, 星标, Favorite, Bookmark(那是 F3 里另一个真实存在的东西)

**Evidence**:
一次功能验证的完整记录,由多个 Case 组成,最终导出为**一个** Excel 文件交付出去。
_Avoid_: 証跡, エビデンス, Proof, Verification record

**Case**:
Evidence 里的一个测试用例。导出后对应 Excel 里的一个 sheet;sheet 是它导出后的形态,不是它本身。名字是测试用例编号,由记录者自己填,不一定是数字(如 `2~5`)。
_Avoid_: Sheet, Test, Scenario, 用例集

**Block**:
Case 里的一段内容,在 Case 内有序。三种:文字、图片、表格。可以带一个 label 作为小标题(如「事前準備の DB データ」)。一个图片 Block 装一张图。
_Avoid_: Entry, 条目, 步骤, Step, Section

**Bookmark**:
一个指向本机文件或文件夹的**入口**,不是那个文件本身。同一个路径可以登记多条 Bookmark,各有自己的名字和位置 —— 那不是重复,是两个不同的入口。
_Avoid_: Shortcut, 快捷方式(Windows 上 `.lnk` 是另一个真实存在的东西), Link, 收藏夹

**Group**:
一批**要一起打开**的 Bookmark。它的意义在「一键全开」,不是分类 —— 这是它和标签的根本区别。一个 Bookmark 属于零或一个 Group。
_Avoid_: Folder, 文件夹(会和 Bookmark 指向的东西撞), Category, 分类, 标签, Collection

**Todo**:
一件待办。有一个可选的**说明**记下这件事到底是什么。
_Avoid_: Task(F4 的脚本执行会带来「任务」这个词), Item, TODO(全大写是代码注释里的那个)

**说明(Description)**:
Todo 上的一段文字,写清楚那件事是什么。形态和 Memo 的正文一样(纯文本 + Markdown),
但它**不是一条 Memo** —— 它没有自己的创建时间,不参与搜索,不能置顶,Todo 一删它就没了。
_Avoid_: 正文(那是 Memo 的), 备注, Note, 详细描述(「说明」已经够)

**草稿(Draft)**:
**一次编辑**里还没保存的内容。它活到**保存成功**或**被明确放弃**为止 —— 收起编辑器、切到别的页面、刷新、关掉浏览器,都不会让它消失。
单位是那一整块「为了改一件事而打开的东西」,不是单个输入框:Todo 的标题和说明一起打开、一起构成一份草稿。
只有**独立的单行编辑**(用例编号、Block 小标题、Evidence 标题)没有草稿 —— 那是「双击、改一个词、回车」,重打一遍的成本接近零。
_Avoid_: 自动保存, Autosave(它从不往服务器写), 缓存, 临时内容

> Memo 与 Evidence 是**两个独立的概念**,不是同一个东西的两种视图。它们表面都是「文字 + 图片的序列」,但 Memo **除置顶外无序**、长期沉淀、靠搜索捞回;Evidence 分用例、每个用例内有序、导出后使命即完成。两者只共享图片的存储机制,不共享领域模型。详见 [ADR-0001](./docs/adr/0001-memo-and-evidence-are-separate-concepts.md)。

> Todo 的说明与 Memo 的正文**形态相同,概念不同**。相同的是「人写的一段字」这个机制;不同的是生命周期 —— Memo 是一条**记录**,独立存在、能被搜索捞回、能置顶;说明是**一件事的附注**,离开那件待办就不存在。这和 ADR-0001 给 Memo / Evidence 划的是同一条线:共享机制,不共享概念。详见 [ADR-0012](./docs/adr/0012-a-todo-description-is-not-a-memo.md)。

> Bookmark 与它指向的文件也是**两个东西**。Bookmark 是一个入口:它有自己的名字、自己在组里的位置,而同一个文件可以有两个入口。所以「同一路径已存在」不是一个需要去重的错误。详见 [ADR-0006](./docs/adr/0006-a-bookmark-is-an-entry-not-a-file.md)。
