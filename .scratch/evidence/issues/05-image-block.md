# 05: 图片 Block

**What to build:** 在 Case 里粘贴或拖拽截图,成为图片 Block。接 02 提出来的 `core/images.py`,存到 `data/images/evidence/<evidence_id>/`。

**一个 image Block 装一张图。** 一次粘 3 张就是 3 个 Block,各自可以加 label、可以单独排序 —— 这也是下面那条删除规则成立的前提。

**删除规则和 memo 相反,这是刻意的,不要「统一」回去。** memo 不做引用计数,是因为图片引用藏在 Markdown 正文里,剪切一段文字的中间态引用数为 0,按计数删会造成不可逆误删。Evidence 里这个前提不成立:引用是**结构化的**,一个 image Block 就是一张图,没有中间态 —— 删一个 image Block 就是明确地说「这张不要了」。所以:删 Block 即删文件、删 Case 即删其名下所有图片、删 Evidence 即删整个目录。

沿用 memo 那条「**删不掉文件不算失败**」:Windows 上被看图软件占着的截图删不掉,而 DB 行已经没了,这时回一个错误等于撒谎。

图片**原图存储、不压缩**(缩放只发生在导出时,见 07)。截图不接受 `.svg`,非白名单扩展名一律记为 `.png`,图片响应加 `X-Content-Type-Options: nosniff` —— 和 memo 同一条安全线,由 `core/images.py` 统一保证。

**Blocked by:** 02, 04

**Status:** ready-for-agent

- [ ] 在 Case 里粘贴剪贴板截图,生成一个图片 Block
- [ ] 也能把图片文件拖拽进来
- [ ] 一次粘贴多张 = 多个 Block,顺序与粘贴顺序一致
- [ ] 图片存 `data/images/evidence/<evidence_id>/`,原图不压缩
- [ ] 图片 Block 可以加 label、可以参与排序
- [ ] 删 image Block → 文件从磁盘上消失
- [ ] 删 Case → 它名下所有图片文件消失
- [ ] 删 Evidence → 整个目录消失
- [ ] 文件删不掉时接口仍然成功返回
- [ ] HTTP 主接缝测试覆盖上述三级删除与「删不掉不算失败」
