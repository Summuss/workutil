# workutil

一个自用的本地开发效率工具,把日常开发中高频而琐碎的动作收进同一个地方。

## Language

**Memo**:
随手记下的一则琐碎信息,可以包含文字和图片。一次保存产生一条 Memo,粒度由记录者当场决定。
_Avoid_: Note, 笔记, 碎片信息

**Evidence**:
一次功能验证的完整记录,由有序的步骤组成,最终导出为 Excel 文件交付出去。
_Avoid_: 証跡, エビデンス, Proof, Verification record

> Memo 与 Evidence 是**两个独立的概念**,不是同一个东西的两种视图。它们表面都是「文字 + 图片的序列」,但 Memo 无序、长期沉淀、靠搜索捞回;Evidence 有序、带步骤编号、导出后使命即完成。两者只共享图片的存储机制,不共享领域模型。详见 [ADR-0001](./docs/adr/0001-memo-and-evidence-are-separate-concepts.md)。
