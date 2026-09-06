# 怎么跑起来

> 本文只讲**操作步骤**。为什么是这个形态见 [design.md](./design.md) §1 与 §7。

三个场景,别搞混:

| 场景 | 服务跑在哪 | 用哪个端口 | 什么时候用 |
| --- | --- | --- | --- |
| A. 开发 | 服务器 | 5173(Vite) | 改代码,要热更新 |
| B. 验收 | 服务器 | 8765(FastAPI) | 验的就是将来在工作机上跑的那个东西 |
| C. 使用 | 工作机 / 私人 Mac | 8765 | 日常真正用它 |

## 零、一次性准备(服务器)

```sh
cd ~/Code/summus-workutil
make install          # backend: uv sync;frontend: pnpm install
```

需要 [uv](https://docs.astral.sh/uv/) 和 Node + pnpm。服务器上都已经有了。

> **所有 `make` 命令都在仓库根目录跑。** 在 `backend/` 里跑会得到
> `make: *** No rule to make target` —— Makefile 只有一份,在根目录。

---

## A. 开发(日常)

### 1. 从 macOS 开隧道

```sh
ssh -L 5173:127.0.0.1:5173 summus@192.168.3.3
```

**只用转发 5173。** `/api` 由 Vite 在服务器端反代到 8765,不需要第二条隧道。

### 2. 在服务器上起两个进程

```sh
make dev-backend     # :8765,--reload
make dev-frontend    # :5173
```

要两个 shell。用 tmux 一步到位:

```sh
tmux new-session -d -s workutil 'make dev-backend'
tmux split-window -t workutil 'make dev-frontend'
tmux attach -t workutil
```

`Ctrl+b d` 脱离,`tmux attach -t workutil` 回去,`tmux kill-session -t workutil` 结束。

验证两个都活着:

```sh
tmux list-panes -t workutil        # 应该两个 pane,dead=0
curl -sS localhost:5173/api/memos  # 经 Vite 反代打到后端,通了就说明隧道够用
```

### 3. 在 macOS 浏览器打开

<http://localhost:5173>

改前端存盘即刷新;改后端 `--reload` 会自己重启。

---

## B. 验收(生产形态)

一个端口、一条命令,验的是最终形态:前端构建产物由 FastAPI 一并托管,单进程。

```sh
# macOS 上
ssh -L 8765:127.0.0.1:8765 summus@192.168.3.3

# 服务器上
cd ~/Code/summus-workutil && make build && make run
```

打开 <http://localhost:8765>。

### UI 要人工看什么

第一版**刻意不写前端自动化测试**(见 `.scratch/memo/spec.md` Testing Decisions),
所以 UI 回归只能靠手动。每次动了前端,对着看一遍:

| 看什么 | 期望 |
| --- | --- |
| 页面打开的瞬间 | 光标已经在输入框里,不点任何地方直接打字就有字 |
| 打几个字,`Ctrl+Enter` | 立刻出现在下方列表最上面,只显示首行 |
| 保存之后 | 输入框空了,而且**还是聚焦的**,可以直接接着打下一条 |
| 连记三条 | 最新的在最上面 |
| `F5` 刷新 | 都还在,顺序不变 |
| 记一条多行的(粘段报错堆栈) | 列表里只显示第一行,不是整坨 |
| 只打空格然后 `Ctrl+Enter` | 什么都不发生,不产生空记录 |
| **保存后马上接着打字** | 已保存的那段不会赖在框里(否则下次保存会存重复) |

macOS 上 `Cmd+Enter` 等价于 `Ctrl+Enter`。

---

## C. 在工作机 / 私人 Mac 上使用

```sh
make build   # 构建前端(需要 Node)
make run     # 启动
```

打开 <http://127.0.0.1:8765>。

**运行时只需要 Python(uv),不需要 Node** —— 前端已经是构建好的静态文件
(design.md §3.1)。但 `frontend/dist/` 不进版本库,所以目标机上要么自己
`make build` 一次(那就需要 Node),要么把 `dist/` 拷过去。

> ⚠️ **最终分发方式还没定**,取决于工作机允不允许装软件(requirements.md §6)。
> 若不允许,退路是 uv 自带 Python + PyInstaller 打包(design.md §3.2),届时这一节要重写。

### 落差:有些东西在服务器上验不了

开发时服务跑在 Linux 服务器上,所以后续里程碑的这些行为**必须拿到 Windows / macOS 本机上测**:

- F3 书签「用默认程序打开文件」—— 在服务器上会去开服务器的文件,而服务器没有桌面
- F4 脚本执行 —— 跑的是服务器上的 Python

UI、数据存取、Excel 导出可以在服务器上完整验证。详见 design.md §7、§9。

---

## 常用命令

| 命令 | 做什么 |
| --- | --- |
| `make install` | 装两端依赖 |
| `make dev-backend` | 后端 :8765,热重载 |
| `make dev-frontend` | 前端 :5173,`/api` 反代到后端 |
| `make build` | 构建前端到 `frontend/dist/` |
| `make run` | 生产形态启动(单进程,含 UI) |
| `make test` | 后端测试 |
| `make check` | ruff + mypy + tsc |

改了 ORM 模型之后要生成迁移:

```sh
cd backend && uv run alembic revision --autogenerate -m "描述"
```

迁移**随服务启动自动执行**,不用手动 `upgrade`。生成后过一眼再提交。

## 数据在哪

| 平台 | 位置 |
| --- | --- |
| Windows | `%APPDATA%\workutil` |
| macOS | `~/Library/Application Support/workutil` |
| Linux | `~/.local/share/workutil` |

里面是 `workutil.db` 和 `images/`,目录内部只用相对路径。
**把这个目录整个拷走就是一份完整备份**,不需要工具提供导出功能。

设环境变量 `WORKUTIL_DATA_DIR` 可以指向别处 —— 开发时想要一份干净的库很方便,
试出来的垃圾数据不会混进真正在用的那份:

```sh
WORKUTIL_DATA_DIR=/tmp/workutil-scratch make run
```

**删除功能还没做**(票 03),所以现在清掉试出来的记录只能删库文件:

```sh
rm ~/.local/share/workutil/workutil.db     # 下次启动会自动重建
```

## 出问题时

**浏览器打不开** —— 十有八九是隧道断了,不是服务挂了。先在服务器上确认服务活着:

```sh
curl -sS localhost:8765/api/memos
```

有输出就说明服务没问题,重开 `ssh -L` 即可。

**端口被占** —— 上一次的进程没退干净:

```sh
ss -tlnp | grep -E '5173|8765'
pkill -f 'uv run workutil'; pkill -f uvicorn
```

**局域网里另一台机器访问不了** —— 这是设计如此,不是故障。服务只绑 `127.0.0.1`,
因为它后续会具备执行任意本地 Python 的能力(requirements.md §5)。所以必须走 SSH 端口转发,
Tailscale IP 也进不来。
