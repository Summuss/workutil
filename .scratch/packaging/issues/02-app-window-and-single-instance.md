# 02: 独立窗口与「已经在运行」

**What to build:** 让 `python -m app` 在打包模式下起完服务就开一个**独立窗口**,并把「重复双击」变成一件无害的事。

**开窗是 `core/platform.py` 的第三个动词。** 那一层已经有 `open(path)` 和 `reveal(path)`,加 `open_app_window(url)` 完全同构 —— 一样是「交给系统之后不再关心」,一样按平台分实现,一样能用现成的 fake 注入测试。Linux 实现照例抛 `UnsupportedPlatformError`,所以服务器上开发时不会去尝试开窗。

| 平台 | 依次尝试,失败退到下一个 |
| --- | --- |
| Windows | `msedge --app=<url>` → `chrome --app=<url>` → `start <url>` |
| macOS | `open -na "Google Chrome" --args --app=<url>` → Edge 同理 → `open <url>` |
| Linux | `UnsupportedPlatformError` |

用**独立的 `--user-data-dir`**(放数据目录下):窗口因此不受公司浏览器策略、扩展和「清除浏览数据」影响,`localStorage` 里的展开状态与语言偏好才稳定。

**「端口已占用」不是错误,是「已经在跑」**:打印一句话、开窗、**退出码 0**。于是重复双击的表现是「把已有窗口拿到眼前」,而不是弹一个看不懂的报错。

**开窗只在打包模式发生**,由启动器设 `WORKUTIL_OPEN_WINDOW=1` 触发 —— 否则 `make dev-backend` 会在服务器上尝试开浏览器。开窗时机挂 uvicorn 的 lifespan 启动钩子,保证已经在监听才开,不靠 sleep 猜。

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] `core/platform.py` 新增 `open_app_window(url)`,三个平台实现按上表
- [ ] `tests/fake_platform.py` 跟着记录这个调用
- [ ] Linux 实现抛 `UnsupportedPlatformError`,与 `open`/`reveal` 一致
- [ ] 用独立 `--user-data-dir`,路径在数据目录下
- [ ] 启动时端口被占用 → 打印「已经在运行」、开窗、退出码 **0**
- [ ] 开窗只在 `WORKUTIL_OPEN_WINDOW=1` 时发生,默认不开
- [ ] 开窗挂在 lifespan 启动钩子上,不用 `sleep` 等服务起来
- [ ] `GET /api/version` 返回 `pyproject.toml` 的版本
- [ ] 导航栏 workutil 字样旁边小字显示版本(手动更新分发,必须看得出装的是哪个版本)
- [ ] 测试:打包模式启动 → fake platform 收到了 `http://127.0.0.1:8765`
- [ ] 测试:非打包模式启动 → 平台层**没有**收到开窗调用
- [ ] 测试:端口占用时退出码为 0 且仍然开窗
- [ ] 测试:`GET /api/version`
- [ ] `make check` 与 `make test` 通过
