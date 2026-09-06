# workutil

一个自用的本地开发效率工具。背景与需求见 [docs/requirements.md](docs/requirements.md),
技术设计见 [docs/design.md](docs/design.md),术语见 [CONTEXT.md](CONTEXT.md)。

## 运行(Windows / macOS)

需要 [uv](https://docs.astral.sh/uv/)。前端构建产物由 FastAPI 一并托管,所以**运行时不需要 Node**。

```sh
make build   # 构建前端(需要 Node,通常在开发机上做一次)
make run     # 启动服务
```

然后打开 <http://127.0.0.1:8765>。服务只监听回环地址,局域网内无法访问。

数据放在平台惯例目录(Windows `%APPDATA%/workutil`,macOS `~/Library/Application Support/workutil`),
里面是 `workutil.db` 和 `images/`。**把这个目录整个拷走就是一份完整备份。**
设 `WORKUTIL_DATA_DIR` 可以指向别处。

## 开发(无桌面 Linux 服务器)

```sh
make install
make dev-backend    # :8765
make dev-frontend   # :5173,/api 反代到后端
```

两个端口都只绑定 127.0.0.1,从 macOS 用 SSH 端口转发访问。

```sh
make test    # 后端测试
make check   # ruff + mypy + tsc
```

数据库迁移随服务启动自动执行。改了 ORM 模型之后:

```sh
cd backend && uv run alembic revision --autogenerate -m "描述"
```
