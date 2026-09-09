# 01: 导出数据包

**What to build:** 新模块 `backend/app/modules/transfer/`(`router.py` / `service.py` / `schemas.py`,**没有 `models.py`** —— 它不拥有任何表),以及 `GET /api/transfer/export`。

**必须用 `sqlite3.Connection.backup` 取快照,不能直接拷 `workutil.db` 文件。**

库**没有开 WAL**(`core/db.py` 的 `create_engine` 不设任何 pragma,SQLite 默认是 rollback journal),拷贝撞上一个进行中的事务就会得到一个半新半旧或损坏的库 —— 而这个包的用途是换电脑,**发现损坏的时候旧电脑可能已经不在手上了**。这是这份 spec 里唯一一个「不做就会在最坏的时刻发现」的技术点,标准库自带,几行的事。

**zip 内容:**

- `workutil.db` —— backup 出来的快照
- `images/` —— 全部,保持相对结构(`images/<memo_id>/`、`images/evidence/<id>/`)
- `manifest.json` —— workutil 版本、**alembic revision**、导出时间、各表条数

manifest 是票 02 那道版本校验的载体;条数是白捡的,导入完能对一眼数字。

**走临时文件,不在内存里拼。** images 可能几百 MB,`BytesIO` 会直接把它顶进内存。写临时文件 → `FileResponse` → 响应完删掉。

文件名 `workutil-data-<YYYYMMDD-HHMM>.zip`,纯 ASCII,不需要 evidence 导出那套 RFC 5987 处理。

模块记得在 `modules/registry.py` 里加一行。

**Blocked by:** 无

**Status:** resolved

- [x] `modules/transfer/` 四件套(无 `models.py`),`registry.py` 加一行
- [x] `GET /api/transfer/export` 返回 zip
- [x] 数据库用 `sqlite3.Connection.backup` 取快照,**不是文件拷贝**
- [x] zip 里含 `workutil.db`、完整的 `images/`、`manifest.json`
- [x] manifest 含 workutil 版本、alembic revision、导出时间、各表条数
- [x] 走临时文件,响应结束后删除,不残留
- [x] 文件名形如 `workutil-data-20260910-1530.zip`
- [x] 测试:导出的 zip 能解开,db 能被 sqlite 正常打开,行数与源库一致
- [x] 测试:evidence 的图片文件在 zip 里,路径结构与数据目录一致
- [x] 测试:manifest 的 revision 与当前 alembic head 一致
- [x] 测试:导出后临时文件不残留
- [x] `make check` 与 `make test` 通过
