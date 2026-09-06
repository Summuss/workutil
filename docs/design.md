# workutil 技术设计

> 本文描述**怎么实现**。需求背景与功能定义见 [requirements.md](./requirements.md)。

## 1. 架构判断

**形态:本地 Python 服务 + 浏览器 Web UI,只监听 `127.0.0.1`。**

推导过程:

1. **F3 / F4 / F5 都必须访问「用户当下正在用的那台电脑」的本地资源** —— 打开本地文件、执行本地 Python、读本地剪贴板截图、写本地 Excel。
2. 因此工具**不能只部署在家里的 Linux 服务器上、用浏览器远程访问** —— 那样操作的是服务器的文件和剪贴板,而不是工作机的。它必须作为本地应用分别运行在 Windows 和 macOS 上。
3. 而开发又在**无桌面的 Linux 服务器**上进行,意味着 UI 必须能在浏览器里开发调试(SSH 端口转发到 macOS),不能依赖本机 GUI 窗口。

两个约束叠加,指向「Web UI + 本地后端」。后端选 Python 是因为**三个最难的需求恰好都落在 Python 生态最成熟的地方**:F4 本来就要跑 Python、F5 的 Excel 嵌图靠 openpyxl、图片处理靠 Pillow。

> 曾考虑 Electron(分发体验最好,但无桌面服务器上无法直接调试,且 Excel 嵌图用 exceljs 比 openpyxl 麻烦)与 Tauri(体积最小,但要写 Rust,且 macOS 版必须在 macOS 上构建)。均因与上述约束冲突而未采用。

## 2. 技术选型

| 层 | 选型 | 理由 |
| --- | --- | --- |
| 后端 | FastAPI + uvicorn | F4 需要 SSE 流式输出脚本日志,异步是刚需 |
| 前端 | React + TypeScript + Vite | 服务器已有 Node 22 / pnpm 10 |
| 样式 | Tailwind CSS | |
| 代码编辑器 | CodeMirror 6 | F4 脚本编辑。比 Monaco 轻得多,够用 |
| 数据库 | SQLite + SQLAlchemy 2.0 + Alembic | 功能会陆续增加,schema 一定会变,迁移能力从一开始就要有 |
| 图片存储 | 磁盘文件,DB 只存相对路径 | 截图体积大,存 BLOB 会撑爆 DB 且难备份 |
| Excel | openpyxl | 图片嵌入与定位是它的强项 |
| 图像处理 | Pillow | 缩略图、格式转换、尺寸计算 |
| 路径 | platformdirs | 跨平台数据目录 |

## 3. 影响全局的决定

### 3.1 生产环境由 FastAPI 直接托管前端构建产物

前端构建在开发服务器上完成,产物交给 FastAPI 作为静态文件托管。

**这样工作机上只需要 Python,不需要 Node。** 直接减少一半的环境依赖 —— 在「工作机能否装软件」尚未确认的情况下,这是重要的风险对冲。

### 3.2 用 `uv` 管理 Python 环境

`uv` 是单文件二进制,并且能自己安装 Python。万一工作机不允许安装软件,这是最好的退路;届时再用 PyInstaller 打包成免安装版也不必改动架构。

### 3.3 平台操作收敛到一层抽象

打开文件、打开文件夹、执行脚本这三类原生操作,全部收敛到 `core/` 下的一层抽象接口,Windows / macOS / Linux 各一个实现。

这既是跨平台的需要,也**把「在服务器上无法验证」的风险圈进一个可替换的小范围**(见 §7)。

| 操作 | Windows | macOS |
| --- | --- | --- |
| 打开文件 | `os.startfile(path)` | `open <path>` |
| 打开所在文件夹 | `explorer /select,<path>` | `open -R <path>` |

## 4. 项目结构

新增一个功能 = 加一个目录 + 一行注册。

```
backend/app/
  core/            配置、DB、平台操作抽象层
  modules/
    memo/          router.py  models.py  service.py  schemas.py
    todo/
    bookmark/
    script/
    evidence/
  main.py          注册各模块 router、托管前端产物
frontend/src/
  features/
    memo/  todo/  bookmark/  script/  evidence/
  shared/          通用组件、API client、图片粘贴 hook
```

每个后端模块四个文件职责固定:`router.py` 只管 HTTP、`service.py` 放业务逻辑、`models.py` 是 ORM 模型、`schemas.py` 是出入参。业务逻辑不依赖 FastAPI,便于单测。

## 5. 数据设计

- **位置**:由 `platformdirs` 决定 —— Windows `%APPDATA%/workutil`,macOS `~/Library/Application Support/workutil`
- **结构**:`workutil.db`(SQLite)+ `images/` 目录
- **不做跨机同步**(见需求文档 §3),因此不需要处理冲突合并,也不需要全局唯一 ID
- **图片**:存为磁盘文件,DB 只记录相对路径。相对路径而非绝对路径,是为了整个数据目录可以直接打包备份、迁移

## 6. 各功能实现要点

### F1 Memo

- **图片粘贴走浏览器的 `paste` 事件**拿到 Blob 后上传,而不是后端读系统剪贴板。这样跨平台一致、无需额外依赖,且不受「服务跑在哪台机器」影响
- 检索用 SQLite 的 **FTS5** 全文索引;分类用标签(多对多),不做文件夹层级 —— 层级正是记事本管不好的原因
- 正文 Markdown,存原文,渲染在前端

### F2 Todo

- 独立表,但保留可空的 `source_memo_id` 外键以支持从 memo 转出后的回溯

### F3 书签

- 调用 §3.3 的平台抽象层
- 「一键打开整组」需要限制并发数并串行间隔,避免一次唤起过多进程
- 失效检测在列表加载时批量 `os.path.exists`,不阻塞渲染

### F4 Python 脚本

- `subprocess.Popen` 执行,解释器路径可配置(默认 `sys.executable`)
- 输出经 **SSE** 推送到前端,而非 WebSocket —— 单向流,SSE 更简单
- 需要保存进程句柄以支持中断;中断要终止整个进程组,避免子进程遗留
- **安全**:服务只绑定 `127.0.0.1`。这是本设计中唯一具备任意代码执行能力的部分,不允许监听 `0.0.0.0`

### F5 Evidence

- 复用 F1 的图片链路
- 条目表带 `order` 字段支持拖拽排序
- **Excel 导出是本功能最琐碎的部分**:openpyxl 不会自动适配行高列宽,需要读取图片像素尺寸,按「像素 → 磅/字符宽度」的换算规则自己计算行高列宽,并对过大的图片做等比缩放
- 排版参数(列宽、最大图片宽度、是否加边框等)做成配置。当前虽是自由格式,但公司若日后要求套模板,不至于推倒重来

## 7. 开发方式,以及一个必须知道的落差

**开发**:服务器上跑 `uvicorn --reload`(:8765)+ `vite dev`(:5173),SSH 端口转发到 macOS,在 macOS 浏览器里开发。

**使用**:在 Windows / macOS 本机启动服务,浏览器打开 `localhost`。

> ⚠️ **落差**:开发时服务跑在 Linux 服务器上,所以 F3 的「打开文件」会去开服务器上的文件(而服务器没有桌面)、F4 执行的是服务器上的 Python。
>
> **这些原生行为无法在服务器上真实验证,必须拿到 Windows / macOS 本机上测。**
>
> §3.3 的平台抽象层就是为了把这部分风险圈在一个可替换的小范围里。UI、数据存取、Excel 导出则可以在服务器上完整验证。

## 8. 实现顺序

| 里程碑 | 内容 | 为什么排这里 |
| --- | --- | --- |
| M0 | 项目骨架:FastAPI + Vite + SQLite + 模块化结构 + 启动脚本 | 后面全部依赖它 |
| M1 | **F1 Memo** | 打通「粘贴图片 → 存储 → 检索」这条最核心的链路 |
| M2 | **F5 Evidence** | 直接复用 M1 的图片链路,只加 Excel 导出;省时间效果最明显 |
| M3 | **F3 书签 + F2 Todo** | 都很简单,一起做,立刻产生日常价值 |
| M4 | **F4 Python 脚本** | 需要流式输出和进程管理,最独立也最复杂,放最后 |

M1 排在 M2 之前,是因为 Evidence 需要的图片链路和 Memo 完全一样 —— **先在更简单的场景里把它做对**。

## 9. 验证方式

| 阶段 | 验证内容 | 在哪验证 |
| --- | --- | --- |
| M0 | 前后端启动,浏览器经端口转发打开页面并调通一个 API | 服务器 |
| M1 | Ctrl+V 粘贴截图能保存并回显;关键词能检索到正文 | 服务器 |
| M2 | 导出的 Excel 下载到 macOS,用 Excel / Numbers 打开,确认图片位置、行高列宽正常 | 服务器 + macOS |
| M3 | 书签用默认程序打开文件、打开所在文件夹;分组一键打开 | **必须在 Windows 本机** |
| M4 | 脚本输出实时滚动而非跑完才出现;中断能真正杀掉进程 | **必须在 Windows 本机** |
| 全流程 | 完整走「改完功能 → 粘贴截图 → 补说明 → 导出 Excel」,与手工做 evidence 对比耗时 | **工作机** |
