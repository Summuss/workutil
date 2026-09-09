# 独立窗口用浏览器的 app 模式,不做原生窗口

design.md §1 从第一天就记着一个产品风险:F1 的「极低摩擦」实际路径是「切到浏览器 → **找到 workutil 标签页** → 输入」,未必快过一直开着的记事本。做成一个有自己图标、能 alt-tab 的独立窗口,能吃掉这个风险的大半。

**做法是 `msedge --app=http://127.0.0.1:8765` 加一个 web manifest**,不是 pywebview、Electron 或 Tauri。得到的是:无地址栏无标签栏的窗口、独立的任务栏图标、Edge 可以「安装为应用」从而获得开始菜单条目和**它自带的开机自启开关**。`127.0.0.1` 算 secure context,装 PWA 不需要 HTTPS。

pywebview 是认真评估过的,体积也不是问题(Windows 依赖链 pywebview + pythonnet + clr-loader + cffi + pycparser 一共 2.4MB)。否掉它的是**验证成本**:它的 GUI 循环要占主线程、uvicorn 得挪进后台线程,而这整套东西**在无桌面的 Linux 开发服务器上一次都跑不了** —— 唯一的测试环境会变成工作机,也就是最难调试的那台。

## Consequences

- **这不算推翻 design.md §1。** 那里否掉的是 Electron(要打包一个浏览器引擎,且无桌面服务器上没法调试)和 Tauri(要写 Rust,且 macOS 版必须在 macOS 上构建)。本决定一个新构建产物都不引入,UI 仍是同一个 FastAPI 托管的前端,只是换了个方式打开同一个 URL。
- **favicon 与 manifest 因此是功能而不是装饰。** 没有它们,app 模式窗口的任务栏图标是个空白方块,PWA 也装不上 —— 而「找到那个窗口」正是这件事要解决的问题。好在这部分是纯前端,**在服务器上就能完整验证**。
- **拿不到的东西要说清楚**:没有全局热键(仍在 requirements.md §7 挂着);`Ctrl+W` 照样关窗口;任务管理器里它还是一个 Edge 进程。
- **窗口用独立的 `--user-data-dir`**,不共用日常浏览器的配置。这样它不受公司浏览器策略、扩展、以及「清除浏览数据」影响,`localStorage` 里的展开状态和语言偏好才稳定。
- **这个决定是可增量反转的。** 哪天 app 模式不够用了,pywebview 是加在上面的一层,前面做的图标和 manifest 一点不浪费 —— 所以现在没有理由先付那份验证成本。
