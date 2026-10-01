# 03: 红框导出成 Excel 里能拖的四边形

**Status:** ready-for-human —— 代码完成;剩下在 Excel 里实机看的几条

**Blocked by:** 01

**What to build:** 导出时,每个红框变成 Excel 里的一个原生四边形:无填充、红色、2.25pt,压在截图的对应位置上,点得中、拖得动、删得掉。为什么不把框画进图片,以及为什么要改写 XML,见 [spec](../spec.md)。

- `LayoutSettings` 加 `box_color = "FF0000"`、`box_line_pt = 2.25`。
- `build_evidence_workbook` 照旧生成工作簿,截图的缩小副本、预留行都不动。`wb.save` 之后,对 xlsx 做**一次后处理**:改写 `xl/drawings/drawingN.xml`,把四边形补进去。这一步放在 `layout.py` 旁边单独一个模块,对外只接收「xlsx 的字节 + 每个 sheet 里每张图的框」,返回新的字节。
  - **sheet 对应哪个 drawing,要从 `xl/worksheets/_rels/sheetN.xml.rels` 里读,不要按序号猜。** 没有图片的 sheet 没有 drawing,一猜就会错位。
  - drawing 里有 `pic` 的 anchor,顺序就是 `ws.add_image` 的调用顺序,按这个顺序和该 sheet 的 image Block 一一对应。数量对不上就抛异常,不能让框落到别的图上。
  - 原图像素换算成 EMU 时,**横向和纵向各用各的比例**:`ext.cx ÷ 原图宽`、`ext.cy ÷ 原图高`。缩放时宽高是分别取整的,共用一个比例,长图底部的框会偏出去。
  - 同一个 drawing 里,形状的 `cNvPr id` 不能和图片重复。
  - **框和截图编成一组**(spec「结论:A,编组」):把这张图的 `xdr:pic` 移进一个 `xdr:grpSp`,组的 `off/ext` 和 `chOff/chExt` 都等于截图自身的 `ext`(原点 0,0),四边形用组内坐标;`pic` 在组内要补上 `a:xfrm`(`off` 0,0,`ext` 等于截图的 `ext`)。写法见原型(分支 `prototype/evidence-annotation-shapes`,`PROTOTYPE_shape_export.py` 的 `mode == "group"`),在 macOS Excel 和 Excel 网页版上验证过
- 没有框的图,drawing 一个字节都不改。整个工作簿都没有框时,直接跳过后处理。
- 写一条 ADR(`0014`):红框导出成 Excel 原生四边形,靠 `wb.save` 之后改写 drawing XML 实现;为什么不把框烧进图片;为什么编组而不是单独摆,附上验证结论。
- 更新 design.md §6 F5 的「Excel 导出」那一节。

### 测试(走导出主接缝)

导出之后拆开 zip,解析 drawing XML,断言下面几条:

- 每张带框的图,四边形的数量和框的数量一致;
- 颜色是 `FF0000`,线宽是 28575 EMU,无填充;
- 四边形相对截图的位置和大小在 1 EMU 的取整误差以内,宽图、长图、小图各测一张。
- 第一个 sheet 没有图、第二个 sheet 有带框的图时,框落在第二个 sheet 上。这一条专门守住「sheet 和 drawing 的对应关系不能按序号猜」。
- `openpyxl.load_workbook` 还能打开这个文件,截图数量不变。

### 验收

- [x] 上面的自动化测试绿
- [ ] 一份带框的 evidence 导出后,用工作机上的 Excel 打开:不弹「修复」;每个框压在对的位置;框能拖、能删
- [ ] 同一份文件用 Mac 上的 Excel 打开,结果一样
- [ ] 在 Excel 里拖动截图,框跟着走;点两下能选中单个框,拖动、删除都正常
- [ ] 把 Excel 的缩放调到 75% / 150%,框和图仍然对得上
- [x] `docs/running.md` 补上这几条手测

## Comments

**2026-10-01 验证结论**(原型 `PROTOTYPE_shape_export.py`,分支 `prototype/evidence-annotation-shapes`):macOS Excel 和 Excel 网页版上,编组和单独摆两种写法都没有弹修复,所有框都压住了目标。用户试用后选编组,理由见 spec。Windows 桌面版 Excel 没有实测,放在上面的验收里。

**实现**(agy 写,host 复核后按 `/code-review` 两轴意见改):`box_export.py` 拆成几个有名字的小函数(sheet 列表、sheet → drawing、一张 drawing 的改写、`a:xfrm`、四边形),入参只留一种形状,样式经 `LayoutSettings.box_style` 传入、不再有第二份默认值;位置测试的期望值改成从 `scale_dimensions` 的显示尺寸独立算出(原先从输出读回的组尺寸推,等于拿代码验代码);两条「清单对不上就拒绝」的测试挪到 `test_evidence_box_export.py`;ADR-0014 按既有 ADR 的体例重写。

真导出一份(宽图两框、长图一框)拆开看:drawing 的结构和原型 `mode == "group"` 逐元素一致,声明只有一行,openpyxl 读得回、图片数不变。剩下三条要在 Excel 里看。
