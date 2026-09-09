# 01: 导出样式对齐 a5m2(字体、表头排版、NULL 灰色)

**What to build:** `layout.py` 里三处样式改动,值全部进 `LayoutSettings`。

**一、字体 `游ゴシック` 11。** 此前是 openpyxl 默认的 Calibri,和既存 evidence 不一样 —— 这是并排放着时最显眼的差别。`LayoutSettings` 加 `font_name: str = "游ゴシック"` / `font_size: int = 11`。

**在 `_text_cell` 这一个漏斗里设,不要改 openpyxl 的 `Normal` 命名样式。** `_text_cell` 已经是「每一格都要经过」的地方(剥控制字符、摁住 `data_type`、写 `@` 格式),字体属于同一类事;`Normal` 是半私有 API,升级会静默变。**把 `Font(...)` 的构造也收进漏斗**,让调用方只传 bold / color —— 否则表头那行、NULL 那格、label 那行三处都得记得带 `name`,漏一处就回到 Calibri。

**二、表头 `wrap_text=True` + `vertical="center"`,数据行不设 alignment。** 这不只是「像」的问题:`loop_kaiin_id` 在 18 宽的列里会被右邻格截断,而**列名是交付内容**。数据行保持不设(默认不换行、底对齐),长值被截断 —— 那正是 a5m2 粘出来的样子。

**三、值恰为 `≪ NULL ≫` 的表格单元格,字体色 `#808080`。**

字符串是 **U+226A + 空格 + `NULL` + 空格 + U+226B**。注意它**不是** `« NULL »`(U+00AB / U+00BB)—— 两者在多数字体里长得几乎一样,复制粘贴时极易搞混。

**匹配必须是精确的:不 trim、不认变体、不用正则。** 数据里真实存在一个长得像 NULL 的字符串是可能的,而 evidence 的底线是「我看到的就是这个值」—— **宁可漏判,不可错判**。实现成 `LayoutSettings` 里一张「字面量 → 字体色」的小表,现在只有一条。

只作用于**表格单元格**;文字 Block 不参与(那里的内容不是结果集)。**判定在导出时按值做**,不在粘贴时打标记 —— 单元格可能被 `PUT .../cells/<row>/<column>` 改过。

**明确不动的:** 列宽 18(a5m2 根本不设列宽,没有对齐对象;18 是为图表共存定的)、表头底色 `#87e7ad`、细边框、`@` 文本格式。

**Blocked by:** 无

**Status:** resolved

- [x] `LayoutSettings` 加 `font_name` / `font_size` / NULL 字面量与颜色的映射
- [x] `_text_cell` 统一设置字体,`Font(...)` 构造收进漏斗,调用方只传 bold / color
- [x] 表头单元格 `wrap_text=True` + `vertical="center"`;数据行不设 alignment
- [x] 表格单元格值为 `≪ NULL ≫` 时字体色 `#808080`
- [x] 列宽、表头底色、边框、`@` 格式**均无变化**(回归)
- [x] 测试:导出后读回,任取一格字体名是 `游ゴシック`、字号 11
- [x] 测试:表头单元格 `alignment.wrap_text` 为真、`vertical` 为 `center`;数据行两者均为默认
- [x] **测试:NULL 的精确匹配** —— 造 `≪ NULL ≫`(变灰)与 `≪NULL≫`、`« NULL »`、`NULL`、`　≪ NULL ≫　`(前后带空白,不变灰)五种值,断言只有第一种是 `#808080`
- [x] 测试:文字 Block 里整段是 `≪ NULL ≫` 时**不**变灰
- [x] 测试:表头底色仍是 `87E7AD`、全表仍有细边框、单元格仍是 `@` 格式(回归)
- [x] `make check` 与 `make test` 通过

