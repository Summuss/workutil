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

> Memo 与 Evidence 是**两个独立的概念**,不是同一个东西的两种视图。它们表面都是「文字 + 图片的序列」,但 Memo 无序、长期沉淀、靠搜索捞回;Evidence 分用例、每个用例内有序、导出后使命即完成。两者只共享图片的存储机制,不共享领域模型。详见 [ADR-0001](./docs/adr/0001-memo-and-evidence-are-separate-concepts.md)。
