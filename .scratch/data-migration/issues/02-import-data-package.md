# 02: 导入数据包(四道门 + 一次备份改名)

**What to build:** `POST /api/transfer/import`,接收上传的 zip。

**这是整个 workutil 里唯一会覆盖既有数据的操作。** 其余所有破坏性动作(删 memo、删 Case、删 Evidence)都作用于单个对象、有确认框、由人当场指定;这一个一次覆盖全部,而触发它的人正处在「刚换了台电脑、什么都还没熟悉」的状态。下面的保守程度是和它的破坏半径相称的,不要精简。

**四道门,顺序如下,任何一道不过就整个拒绝、什么都不动:**

1. **zip 结构合法** —— 有 `manifest.json`、有 `workutil.db`
2. **manifest 的 alembic revision 与当前应用一致** —— alembic 只会向前升级,把新版本导出的包塞进旧版本,结果是一个打不开的库
3. **所有业务表都没有行**
4. **`images/` 目录下没有文件**

**第 3 条的判据不能写成「db 文件不存在」。** 启动时 alembic 已经把表建好了,那个文件**一定存在** —— 这是最容易写错的一处。

**第 4 条不能省。** 「库空但图片还在」是上一次导入失败留下的现场,直接往上盖会留一堆孤儿文件。

**过了四道门之后:**

- 先把现有 `workutil.db` 改名成 `workutil.db.bak-<时间戳>`,**删除留给人手动**
- 解压 db 与 images 到数据目录
- 响应里明确告诉前端**需要重启**

**不自动重启。** SQLAlchemy 的 engine 还连着被换掉的那个文件。自动重启在便携包形态下要杀掉自己再拉起来,和既有的单实例逻辑(design.md §3.5)掺在一起只会更脆 —— 提示人手动关掉再打开。

**解压时注意 zip slip**:zip 里的条目名必须校验,不能让 `../` 写到数据目录外面。这个包正常情况下是自己导出的,但它是从文件系统上传来的,不能假设。

**Blocked by:** 01

**Status:** resolved

- [x] `POST /api/transfer/import`,接收 multipart 上传
- [x] 四道门按顺序校验,各自有独立的错误 code
- [x] **「空」的判据是「所有业务表无行」+「images 无文件」,不是「db 文件不存在」**
- [x] 任何一道不过时,数据目录**一个字节都没被动过**
- [x] 通过后先改名 `workutil.db.bak-<时间戳>`,再解压
- [x] 解压时校验条目名,拒绝任何会写到数据目录之外的路径
- [x] 响应里带「需要重启」的标志
- [x] 测试:**往返** —— 造含 memo / todo / 书签 / evidence + 图片的数据,导出,换空数据目录,导入,逐项断言回来了(evidence 的图片文件也在)
- [x] 测试:库非空时拒绝
- [x] 测试:库空但 images 有文件时拒绝
- [x] 测试:manifest revision 不匹配时拒绝
- [x] 测试:zip 结构非法时拒绝
- [x] 测试:每一种拒绝之后,数据目录内容不变
- [x] 测试:导入成功后数据目录里存在 `workutil.db.bak-*`
- [x] 测试:含 `../` 条目的 zip 被拒绝
- [x] `make check` 与 `make test` 通过

## Comments

**Review 修复(commit `68d749a`)**:实现用了一个泛用的 `TransferError(code, message, status_code)`,`code` 是不带模块前缀的 `SCREAMING_SNAKE_CASE`(`INVALID_ZIP_ARCHIVE` 等),`router.py` 手工拼 `HTTPException` 而不是走既有的 `http_error()`。这和 todo / memo / bookmark / evidence 四个模块统一用的「每种错误一个异常子类,`code = "module.reason"` 类属性,由路由层过 `http_error()` 翻译」的写法不一致 —— 功能上没问题(前端只是 `t(`error.${code}`)` 查表,大小写和有没有模块前缀都能查到),但下一个抄这个模块当模板的人会把这套写法也抄走。

改成 7 个具体异常类(`InvalidZipArchive` / `ZipSlipDetected` / `InvalidZipStructure` / `InvalidManifest` / `AlembicRevisionMismatch` / `DatabaseNotEmpty` / `ImagesNotEmpty`),`code` 统一成 `transfer.snake_case`,消息文案也换成中文(和其余模块的异常消息一致);`router.py` 用一个 `except (...)` 收口后调 `http_error(400, err)`。`error.INVALID_ZIP_ARCHIVE` 等 7 个 i18n key 改名为 `error.transfer.invalid_zip_archive` 等,`zh.json` / `ja.json` 与相关测试断言同步改。

顺带处理了两处:①两个读 `alembic_version` 表的 `except Exception: pass` 收窄成 `except sqlite3.OperationalError`(表不存在时的具体异常),和 8f7f872 那次「收窄 silent except」的清理保持一致;②`manifest.json` 解析成功但不是一个对象(比如 `null`、`[]`)时补一道 `isinstance(manifest_data, dict)` 检查,原来会在后面调 `.get()` 时抛 500 而不是走这道门应有的 400 拒绝。
