# 01: 让程序能在仓库之外运行

**What to build:** 今天 `app/core/config.py` 把前端产物的位置写死成 `Path(__file__).resolve().parents[3] / "frontend" / "dist"` —— 从仓库布局推出来的。便携包里 `app/` 和 `ui/` 是兄弟目录,这个层级不成立,前端会 404 而后端一切正常,症状是「打开是白屏但 `/api/memos` 有数据」。

改成按顺序查找,第一个命中的胜出:

1. `WORKUTIL_UI_DIR` 环境变量
2. 包布局:`app/` 的兄弟目录 `ui/`
3. 仓库布局:`<repo>/frontend/dist`

同时新增 `app/__main__.py`,让 `python -m app` 成为入口(仓库里 `uv run python -m app` 也该能用),便携包的启动器只需要设好 `PYTHONPATH` 再调它。

**Alembic 不要动**:`MIGRATIONS_DIR` 指向 `app/migrations`(包内),`Config()` 是代码里构造的、不读 `alembic.ini`,整个目录拷走就带着。确认一下即可,不需要改。

**Blocked by:** 无

**Status:** done

- [x] `frontend_dist` 改为三级查找,顺序为环境变量 → 包布局 → 仓库布局
- [x] 查找逻辑是一个可单独调用的函数,不埋在 `load_settings()` 里
- [x] 三级都找不到时不抛异常 —— 现在 `create_app` 靠 `settings.frontend_dist.is_dir()` 决定挂不挂 UI,开发时(Vite 当值)本来就没有 dist,这条路径必须保持能走
- [x] 新增 `app/__main__.py`,`python -m app` 等价于现在的 `workutil` 命令
- [x] 测试:摆出三种临时目录布局,断言各自找对了
- [x] 测试:环境变量优先于包布局,包布局优先于仓库布局
- [x] 测试:都不存在时返回一个不存在的路径而不是抛错,`create_app` 仍能起来(回归:开发模式)
- [x] 确认 `app/migrations/versions/*.py` 会随目录拷贝而带走(已确认:MIGRATIONS_DIR 位于 app/migrations,整体拷入包内即可随目录带走,代码中采用编程式 Config 且不依赖 alembic.ini)
- [x] `make check` 与 `make test` 通过
