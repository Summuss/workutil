# workutil

一个自用的本地开发效率工具,把日常开发中高频而琐碎的动作收进同一个地方。

## Language

**Memo**:
随手记下的一则琐碎信息,可以包含文字和图片。一次保存产生一条 Memo,粒度由记录者当场决定。
_Avoid_: Note, 笔记, 碎片信息

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
一件待办。可以由一条 Memo 转出并保留回溯链接,但转出后两者各自独立 —— Memo 不知道自己被转过。
_Avoid_: Task(F4 的脚本执行会带来「任务」这个词), Item, TODO(全大写是代码注释里的那个)

> Memo 与 Evidence 是**两个独立的概念**,不是同一个东西的两种视图。它们表面都是「文字 + 图片的序列」,但 Memo 无序、长期沉淀、靠搜索捞回;Evidence 分用例、每个用例内有序、导出后使命即完成。两者只共享图片的存储机制,不共享领域模型。详见 [ADR-0001](./docs/adr/0001-memo-and-evidence-are-separate-concepts.md)。

> Bookmark 与它指向的文件也是**两个东西**。Bookmark 是一个入口:它有自己的名字、自己在组里的位置,而同一个文件可以有两个入口。所以「同一路径已存在」不是一个需要去重的错误。详见 [ADR-0006](./docs/adr/0006-a-bookmark-is-an-entry-not-a-file.md)。
