# 04: 便携包构建脚本(`make package`)

**What to build:** 一条命令,在**无桌面的 Linux 开发服务器上**产出 Windows 和 macOS 的便携包 zip。

不用 PyInstaller —— 它不能交叉编译。这里之所以能在 Linux 上造 Windows 包,是因为**全部依赖都以预编译 wheel 分发**,我们只是在搬运,不是在编译。已实测:27/27 个 `win_amd64` wheel 下载成功,14MB。

步骤:

1. `uv pip compile pyproject.toml --python-platform windows --python-version 3.12` 解析目标平台依赖。**必须用这个而不是 `uv export`**:后者没有 `--python-platform`,而 `pip download --platform` 又不会求解环境标记,结果是它会去下 `uvloop`(没有 Windows wheel)然后失败
2. `pip download --dest ... --platform win_amd64 --python-version 3.12 --only-binary=:all:` 拉 wheel
3. 从 GitHub 拉 python-build-standalone 的 `install_only_stripped` tarball(Windows x86_64 约 22MB,macOS arm64 约 25MB)
4. `pnpm build` 出前端
5. 解开 wheel 到 `site-packages/`,拼出下面的目录,打 zip

```
workutil/
├── workutil.bat / workutil.command
├── python/          ← 运行时
├── site-packages/   ← wheel 解开
├── app/             ← 后端包(migrations 在内)
├── ui/              ← frontend/dist 的内容
└── README.txt
```

启动器保持**三四行**:设 `PYTHONPATH=site-packages;.`、设 `WORKUTIL_OPEN_WINDOW=1`、调 `python\python.exe -m app`。逻辑都在 ticket 02 的 Python 里,那里能测,`.bat` 里不能。

产物名带版本:`workutil-<version>-windows-x64.zip`。macOS 默认 `aarch64-apple-darwin`,Intel Mac 改一个参数。

**Blocked by:** 01, 02, 03

**Status:** done

- [x] `make package` 产出 Windows 与 macOS 两个 zip,全程在 Linux 上完成
- [x] 用 `uv pip compile --python-platform` 解析依赖(不要用 `uv export`,理由见上)
- [x] wheel 下载失败要**明确报错并中止**,不能产出一个缺包的 zip
- [x] python-build-standalone 的 tarball 下载后校验大小/哈希,不要静默接受一个截断的文件
- [x] `pnpm build` 是构建的一部分,不依赖 `dist/` 恰好还在
- [x] 目录结构如上;`app/migrations/versions/*.py` 确实在包里
- [x] `.bat` / `.command` 只做设环境变量与调用,不含判断逻辑
- [x] `.command` 有可执行位(zip 里也要保住)
- [x] 产物名带 `pyproject.toml` 里的版本号
- [x] 构建产物目录进 `.gitignore`
- [x] 在 Linux 上解开产出的 Windows 包,断言 `app/`、`ui/index.html`、`site-packages/fastapi/`、`python/python.exe` 都在 —— 这是能在服务器上做的最强验证
- [x] `make check` 通过

> **注意:包能否真的跑起来只能在 Windows / macOS 上验。** 这是 `design.md §7` 那条落差的新增项,ticket 05 负责把它写进文档。
