# 01: 平台抽象层

**What to build:** `core/platform.py` —— 把「交给操作系统去打开」这件事收成一层,Windows / macOS / Linux 各一个实现,经 `deps.py` 注入。

**只有两个动词:**

- `open(path)` —— 把路径交给系统,之后不再关心。**文件和文件夹共用这一个**,因为在两个平台上它们本来就是同一个调用
- `reveal(path)` —— 在文件管理器里定位到它

| 操作 | Windows | macOS |
| --- | --- | --- |
| `open` | `os.startfile(path)` | `open <path>` |
| `reveal` | `explorer /select,<path>` | `open -R <path>` |

**F4 的「执行脚本」不进这一层。** 那是 `subprocess` + 流式输出 + 进程句柄,和「交出去就不管」是两种东西,硬共用一个抽象只会让两边都别扭。以后写 F4 时不要往这里加第三个动词。

**Linux 实现明确「不支持」,直接抛错,不调 `xdg-open`。** 开发服务器没有桌面,而 `xdg-open` 在无 `DISPLAY` 的机器上失败得很脏 —— 有时退出码 0 却什么都没发生。把它当「支持」等于让开发时的每一次验证都在撒谎。明确不支持反而有用:UI 上那条错误路径**因此在服务器上每天都会被真实走到**,而它恰好是这个功能里唯一能在服务器上验的部分。

**注入是这张 ticket 的重点,不是顺手做的。** 平台层从 `deps.py` 取,于是 HTTP 测试里换得成一个记录调用的 fake。没有它,ticket 04 的「按顺序打开、跳过失效」就只能靠肉眼在 Windows 上验 —— 而那是全项目唯一验不了的地方(design.md §7)。

**Blocked by:** —

**Status:** ready-for-agent

- [ ] `core/platform.py`:`open` / `reveal` 两个动词,按 `sys.platform` 选实现
- [ ] Windows / macOS 各一个实现,按上表调用
- [ ] Linux 实现抛一个**专有异常**(不是 `NotImplementedError` 泛用型),带一句能直接显示给人看的话
- [ ] 平台层经 `deps.py` 注入,测试可替换
- [ ] `tests/` 里有一个记录调用的 fake,供后续 ticket 使用
- [ ] 有测试:在开发平台(Linux)上调 `open` 抛的是那个专有异常
- [ ] `make check` 通过
