# 07: Excel 导出

**What to build:** M2 的交付口,也是 design.md 点名「最琐碎」的一块 —— 唯一被文件格式硬限制卡住的地方。加 openpyxl + Pillow 依赖(目前都不在 `backend/pyproject.toml` 里)。

**图片不撑行高,而是预留行。** Excel 行高上限 **409 磅**,96 DPI 下 1 px = 0.75 磅,即**一行最多装 545 px** —— 截图基本都比这高,「把行高设成图片高度」这条路是死的(Excel 会截到 409,图片压住下面的内容)。做法:不动行高(默认 15 磅 = 20 px),按 `N = ceil(图片高px / 20)` 预留 N 行,图片浮动锚在第一行。openpyxl 的图片本就不撑开行高,不预留就会重叠 —— requirements.md 验收要点里「不重叠、不溢出」防的正是这个。

宽度靠**等比缩放到最大宽度**(默认 900 px)。**缩放只作用在导出的那一份上,磁盘原图不动** —— 改了参数重导一次就是另一个尺寸,原始画质永远在。

**所有单元格统一写 `@` 文本格式。** `007`、`2024-01-01`、18 位 ID 交给 Excel 自动识别会分别变成 `7` / 日期序列号 / 科学计数法,而 evidence 的全部意义就是「我看到的就是这个值」。代价是「以文本形式存储的数字」绿色三角 —— **接受它,不要去压**:openpyxl 3.1.5 的 `IgnoredErrors` 类没有接到 worksheet 上,压掉它要拆 xlsx 的 zip 手改 XML(见 ADR-0004)。

**不用 Excel Table(ListObject)** —— 它强制列名唯一,DB join 出来的两个 `id` 会被自动改成 `id` / `id2`,交付物里的列名被工具偷偷改掉不能接受。

**同一个 Case 里的多个表格共用列宽** —— 一个 sheet 只有一套列宽。这是 Excel 的形状,不是实现偷懒,不要试图修。

**Blocked by:** 05, 06

**Status:** ready-for-agent

- [ ] `pyproject.toml` 加 openpyxl 与 Pillow
- [ ] `layout.py` 纯函数:像素 → 预留行数、等比缩放后尺寸;带单测,覆盖超高、超宽、极小图
- [ ] `LayoutSettings` dataclass 集中排版参数(列宽、最大图片宽度 900px、底色、边框),值写在代码里,**不做配置文件**
- [ ] 一个 Case 一个 sheet,sheet 名 = Case 名
- [ ] 单列纵向排布:Block 依次往下,之间空一行,label 加粗单占一行
- [ ] 图片按预留行数放置,**下一个 Block 从图片下方开始**
- [ ] 表格:表头加粗 + 底色 `#87e7ad` + 全表细边框;`has_header` 为 false 时不加粗任何行
- [ ] 所有单元格 `@` 文本格式
- [ ] 文件名 `エビデンス_<title>.xlsx`,title 里的 `\ / : * ? " < > |` 替换为 `_`
- [ ] `Content-Disposition` 用 RFC 5987 的 `filename*=UTF-8''...`(文件名是非 ASCII,只给 `filename=` 在部分环境会乱码)
- [ ] 零个 Case 的 Evidence 拒绝导出(422);零个 Block 的 Case 允许,出一个空 sheet
- [ ] 主接缝测试:调导出接口拿 bytes → openpyxl 读回来,断言 sheet 名、单元格值、图片数量与锚定行
- [ ] 护栏用例:1080px 高的图片导出后,**下一个 Block 的起始行在图片下方**(撑行高的实现会在这里失败)
- [ ] 护栏用例:值为 `007` 的单元格读回来仍是字符串 `"007"`
- [ ] 人眼验收:导出的 xlsx 下载到 macOS,用 Excel / Numbers 打开,确认 sheet 名、图片位置、行高列宽正常
