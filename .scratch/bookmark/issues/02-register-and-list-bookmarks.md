# 02: 登记与列表

**What to build:** Bookmark 的表、增删改查,加上前端的书签页(先只有散装书签,组在 03)。`registry.py` 加一行,`AppNav` 加一个 tab,路由 `/bookmarks`。

**路径靠手工粘贴,不做文件选择器 —— 因为做不出来。** 浏览器不把绝对路径交给页面:`<input type="file">` 拿到的 `File` 没有 `path`,拖拽也没有(那是 Electron 才有的)。**不要试图绕**;下一个想「优化」这里的人应该先读 design.md §6 F3。Windows 上 `Shift+右键 → 复制为路径`、macOS 上 `Cmd+Opt+C` 都是一步,而这个痛点的形状是**录入低频、打开高频**,摩擦该压在打开侧。

**登记时校验路径存在,不存在就硬拒绝**,话术直说「这个路径现在不存在」。「粘错了」的概率远高于「登记一个当前没插的 U 盘」,而后者的补救是把盘接上再登记一次;前者会静静躺成一条永远打不开的灰书签。**不做「仍然登记」的二次确认** —— 一个平时用不到的确认按钮只会训练人闭着眼睛点它。改路径走同一道校验。

**不要给 `path` 加 `UNIQUE`,不要提示「已存在」。** 同一个文件登记两条书签是**正常用法**:Bookmark 是一个入口,不是一个文件,同一份 `config.yml` 在两个组里本来就该有不同的名字(ADR-0006)。

`name` 必填、前端**由文件名预填**(可空就得在显示时 fallback,UI 白白多一种状态)。是文件还是文件夹在登记时判定并存下来 —— 04 的 `reveal` 和前端按钮都要用。

**Blocked by:** —

**Status:** done

- [x] `modules/bookmark/`(router / models / service / schemas)+ Alembic 迁移 + `registry.py` 一行
- [x] `POST /api/bookmarks`(path 必填、name 必填、记下是文件还是文件夹)
- [x] `GET /api/bookmarks` / `PATCH {id}`(name·path)/ `DELETE {id}`
- [x] 登记或改成一个不存在的路径 → **400 + 一句人话**,不是 500 也不是静默收下
- [x] **同一个 path 能登记两条**,没有去重、没有 `UNIQUE`
- [x] 前端 `/bookmarks` 页面 + `AppNav` 多一个 tab,能登记、改名、改路径、删除
- [x] 前端粘贴路径后**自动填好 name**(文件名),可改
- [x] 打开 `/` 仍然直接是 memo 输入框、光标已在里面
- [x] HTTP 主接缝测试覆盖上述行为;`make check` 与 `pnpm build` 通过
