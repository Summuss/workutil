# 便携包在 Linux 上组装,不用 PyInstaller

「把 Python 应用打包分发」的第一反应是 PyInstaller。这里**不能用**:它不做交叉编译,而这个项目的开发机是一台无桌面的 Linux 服务器,目标是 Windows 和 macOS。用它就意味着要借一台 Windows 来构建 —— 而「工作机」正是最不该拿来构建的那台机器。

所以改成**组装**而不是打包:python-build-standalone 的运行时 + 预编译 wheel 解开的 `site-packages` + `app/` 与前端产物,拼成一个解压即用的目录。这在 Linux 上完全可行,因为**全部 27 个依赖都以预编译 wheel 分发**(Pillow、pydantic-core、watchfiles 这些带 C / Rust 扩展的也是),我们只是在搬运,不是在编译。整包约 37MB。

## Consequences

- **必须用 `uv pip compile --python-platform windows` 解析依赖,不能用 `uv export`。** 后者没有这个参数;而 `pip download --platform` 又不会按目标平台求解环境标记,于是它会去下 `uvloop` —— 那个包没有 Windows wheel,构建当场失败。这是这条路上唯一一个不直观的坑。
- **顺带避开了杀毒软件误报。** 一堆 `.py` 文件加一个 `python.exe`,比 PyInstaller 的单文件 exe 要不容易触发启发式告警 —— 对一台公司管控的 Windows 来说这不是小事。
- **数据不放包里**,留在 `%LOCALAPPDATA%`。更新因此是「删掉旧文件夹、解压新的」,数据零风险。反过来把数据放进包里虽然更「便携」,但让一个可以被整体拷走的文件夹装着公司数据,与 requirements.md §3 的保密意图相悖。
- **多了一条「在服务器上验不了」。** 包能否真的跑起来只能在目标机上确认(design.md §7 已有的第一条是 F3 用默认程序打开文件)。缓解手段是把逻辑尽量留在 Python 里 —— 端口检测、开窗分派都有自动化测试,启动器 `.bat` 只有三四行不含判断。
- 代价是包体积比「假设目标机有 Python」大 22MB。接受:不依赖工作机上恰好装了什么,正是这个方案存在的理由。
