# Spec: 便携包分发与独立窗口

Status: ready-for-agent

## Problem Statement

功能做完了,但这个工具至今**只能在开发服务器上跑**。工作机上要用它,现在的说明是「`make build` + `make run`」—— 那需要工作机装 Node、装 uv、拉源码,而 `requirements.md §6` 那条「工作机能否自由安装软件」一直挂着没答。

同时还有一个从第一天就记在 `design.md §1` 的产品风险:F1 的「极低摩擦」实际路径是「切到浏览器 → **找到 workutil 标签页** → 输入」。这条路径今天比设想的更差 —— 前端**连 favicon 都没有**(`frontend/` 下没有 `public/` 目录),标签页上是一个空白图标,「找到那个标签页」全靠读标题文字。

## Solution

**分发:一个解压即用的便携包,整个在 Linux 开发服务器上组装。**

不用 PyInstaller —— 它不能交叉编译,而开发机是无桌面 Linux,目标是 Windows 和 macOS。改为把三样东西拼进一个目录:python-build-standalone 的运行时、预编译 wheel 解开的 `site-packages`、以及 `app/` 和前端产物。**全部依赖都以预编译 wheel 分发,所以「组装」不需要编译**,Linux 上就能造出 Windows 包(已实测:27/27 个 win_amd64 wheel 下载成功,14MB)。

**独立窗口:用浏览器的 app 模式,不做原生窗口。**

启动器起完服务后用 `msedge --app=http://127.0.0.1:8765` 开一个无地址栏、无标签栏、有独立任务栏图标的窗口;再补上 favicon 和 web manifest,使它同时能被 Edge「安装为应用」(开始菜单条目 + 独立图标 + Edge 自带的开机自启开关)。`127.0.0.1` 算 secure context,装 PWA 不需要 HTTPS。

**分发渠道:GitHub Release。** 工作机能匿名访问 GitHub 但不能登录,所以仓库需要 public,zip 作为 release 资产下载。

## Domain Model

不引入新领域概念,`CONTEXT.md` 不改。

`core/platform.py` 的动词从两个变成三个:`open(path)` / `reveal(path)` / **`open_app_window(url)`**。第三个和前两个同构 —— 都是「把一件事交给系统,之后不再关心」,都按平台分实现,Linux 照例抛 `UnsupportedPlatformError`。这不是新抽象,是既有抽象长出的第三个动词。

## User Stories

1. 作为使用者,我希望在工作机上解压一个文件夹、双击一下就能用,不需要装 Python、Node 或任何别的东西。
2. 作为使用者,我希望它以一个**独立窗口**出现 —— 有自己的任务栏图标、能 alt-tab 切过去,而不是淹没在一堆浏览器标签页里。
3. 作为使用者,我希望重复双击不会起第二个服务、也不会弹一个看不懂的报错,而是直接把已经在跑的那个窗口拿到眼前。
4. 作为使用者,我希望能把它装进开始菜单并设成开机自启,这样早上开机它就在那儿了。
5. 作为使用者,我希望升级就是「下载新 zip、解压覆盖」,而我的 memo、evidence、书签一条都不会丢。
6. 作为使用者,我希望在界面上看得到当前跑的是哪个版本 —— 因为更新要靠手动下载,不然分不清工作机上装的是不是最新的。
7. 作为开发者,我希望这个包能在无桌面的 Linux 服务器上一条命令造出来,不需要借一台 Windows。

## Implementation Decisions

### 包的形状

```
workutil/
├── workutil.bat            ← Windows:双击这个
├── workutil.command        ← macOS:双击这个
├── python/                 ← python-build-standalone 解开
├── site-packages/          ← 27 个 wheel 解开
├── app/                    ← 后端包(migrations 在包内,跟着走)
├── ui/                     ← frontend/dist 的内容
└── README.txt              ← 一句话说明
```

体积:Python 运行时 22MB(stripped)+ wheel 14MB + 前端 0.7MB ≈ **37MB 压缩**。

- **数据不放包里**,仍然在 `%LOCALAPPDATA%\workutil` / `~/Library/Application Support/workutil`。更新就是「删掉旧文件夹、解压新的」,数据零风险;而且从保密角度,数据跟着一个可整体拷走的文件夹走比留在系统盘更糟,不是更好。
- `user_data_dir` 落在 LOCALAPPDATA 而非漫游目录,截图再多也不会撑爆公司的漫游配置文件 —— 现状已经是对的,不要改成 `roaming=True`。

### 让程序能在仓库之外运行

`config.py` 现在写死 `frontend_dist = Path(__file__).parents[3] / "frontend" / "dist"` —— 从仓库布局推的,便携包里这个层级不成立。改为按顺序找:

1. `WORKUTIL_UI_DIR` 环境变量
2. 包布局:`app/` 的兄弟目录 `ui/`
3. 仓库布局:`<repo>/frontend/dist`

**Alembic 迁移不用动** —— `MIGRATIONS_DIR` 指向 `app/migrations`(包内),`Config()` 是代码里构造的、不读 `alembic.ini`。整个目录拷走就带着。

### 入口与启动逻辑

逻辑放在 Python 里,不放在 `.bat`/`.command` 里 —— 那里能测,这里不能。两个平台的启动器因此都只有三四行(设 `PYTHONPATH`,调 `python -m app`)。

- 新增 `app/__main__.py`,让 `python -m app` 可用(仓库里 `uv run python -m app` 同样可用)。
- **端口已占用 = 已经在跑**,不是错误:打印一句「workutil 已经在运行」,开窗,**退出码 0**。重复双击因此表现为「把窗口拿到眼前」。
- 开窗只在打包运行时发生,由启动器设 `WORKUTIL_OPEN_WINDOW=1` 触发 —— 否则服务器上 `make dev-backend` 会去尝试开浏览器。
- 开窗时机挂在 uvicorn 的 lifespan 启动钩子上,保证服务已经在监听才开窗,不靠 sleep 猜。

### 开窗:`core/platform.py` 的第三个动词

`open_app_window(url)`,依次尝试,失败就退到下一个:

| 平台 | 顺序 |
| --- | --- |
| Windows | `msedge --app=<url>` → `chrome --app=<url>` → `start <url>`(默认浏览器,普通标签页) |
| macOS | `open -na "Google Chrome" --args --app=<url>` → Edge 同理 → `open <url>` |
| Linux | 抛 `UnsupportedPlatformError`(和 `open`/`reveal` 一致) |

用**独立的 `--user-data-dir`**(放在数据目录下),这样这个窗口不受公司浏览器策略、扩展、以及「清除浏览数据」影响,`localStorage` 里那套展开状态和语言偏好也就稳定了。

### favicon、manifest 与 PWA

纯前端工作,**在 Linux 服务器上用浏览器就能全部验证**。

- 新建 `frontend/public/`,放 favicon(SVG + ICO)与 192/512 两个尺寸的 PNG。
- `manifest.webmanifest`:`name`、`short_name`、`icons`、`start_url: "/"`、`display: "standalone"`、`theme_color`、`background_color`。
- `index.html` 里 link 上。
- 图标自己画一个极简的,不引第三方图标库 —— 它要在 16px 的任务栏上认得出来,复杂图案没用。

### 版本可见

手动下载更新意味着「工作机上跑的是哪个版本」会变成真问题。`GET /api/version` 返回 `pyproject.toml` 里的版本,导航栏 workutil 字样旁边小字显示。

### 构建

`make package` 一条命令,在 Linux 上产出 zip:

1. `uv pip compile --python-platform windows --python-version 3.12` 解析出目标平台依赖(它会正确排除 `uvloop`,那个包没有 Windows wheel)
2. `pip download --platform win_amd64 --only-binary=:all:` 拉 wheel
3. 从 GitHub 拉 python-build-standalone 的 `install_only_stripped` tarball
4. `pnpm build` 出前端
5. 拼目录,打成 `workutil-<version>-windows-x64.zip`

macOS 默认出 `aarch64-apple-darwin`(Apple Silicon);Intel Mac 改一个参数即可。

## Testing Decisions

| 位置 | 测? | 理由 |
| --- | --- | --- |
| `frontend_dist` 的三级查找 | ✅ 主接缝 | 给临时目录摆出三种布局,断言各自找对 —— 这是包里最容易静默坏掉的一处 |
| 「端口已占用 → 开窗并退出 0」 | ✅ 主接缝 | 重复双击是必然会发生的操作 |
| `open_app_window` 的平台分派 | ✅ 主接缝 | 复用现有的 fake platform:「打包模式启动 → 平台层收到了这个 URL」 |
| `GET /api/version` | ✅ | 一行的事 |
| favicon / manifest | ❌ | 浏览器里看一眼,`running.md` 手动清单 |
| 构建脚本产出的包能否真的跑起来 | ❌ **只能在目标机上验** | 见下 |

## Out of Scope

| 项目 | 说明 |
| --- | --- |
| pywebview / Electron / Tauri 原生窗口 | 见 ADR-0010。档 1+2 不够用了再说,而且它是增量不是重写 |
| 全局热键 | 仍然要额外的原生入口,`requirements.md §7` 里继续挂着 |
| 自动更新 / 更新检查 | 手动下载 zip 够用;自动更新要处理自我覆盖,不值 |
| 代码签名 / 公证 | 自用工具,没有分发给第三方的需求 |
| Windows ARM64 / Intel Mac | 构建脚本参数化了,真需要时加一行 |
| 安装程序(MSI / pkg) | 便携包的全部意义就是不安装 |

## Further Notes

### 这不算推翻 `design.md §1`

那一节否掉的是 **Electron**(要打包一个浏览器引擎,且无桌面服务器上没法调试)和 **Tauri**(要写 Rust,且 macOS 版必须在 macOS 上构建)。本 spec 一个新构建产物都不引入,UI 仍然是同一个 FastAPI 托管的前端,只是换了个方式打开同一个 URL。真正沾边的只有被划进 Out of Scope 的原生窗口。

### 新增一条「在服务器上验不了」

`design.md §7` 已经记了一条(F3 用默认程序打开文件)。这次再加一条:**便携包本身能否跑起来、app 模式窗口长什么样,只能在 Windows / macOS 上验**。缓解手段是把逻辑尽量留在 Python 里(端口检测、开窗分派都有自动化测试),让真机上要验的收缩成「窗口真的开出来了」。

### 分发渠道的前置条件

GitHub Release 匿名下载要求**仓库是 public**。已扫过:没有邮箱、密钥或公司标识,唯一的真实标识是 `running.md` 里的 `summus@192.168.3.3`(私有网段,应改成占位符)。这一步需要单独确认,见 ticket 05。

### Windows 的 Mark-of-the-Web

从网上下载的 zip 解压后,文件会带 MOTW 标记,双击 `.bat` 可能触发 SmartScreen 警告。**解压前**右键 zip → 属性 → 勾「解除锁定」可以一次性清掉所有解压出来的文件。这条必须写进 `running.md`,否则会在工作机上浪费一个小时。
