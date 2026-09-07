# 03: 删除一条 Memo

**What to build:** 让过时和无用的记录可以被移除,这样列表不会被永远堆满。

**Blocked by:** 02

**Status:** done

- [x] 展开的 Memo 上有删除操作
- [x] 删除后该 Memo 从列表中消失
- [x] 刷新页面后它依然不在
- [x] 删除是直接删除,不做软删除、不保留版本历史
- [x] HTTP 接缝测试:删除后,列表与单条读取都不再返回它

## Comments

代码已实现，后端测试增至 24 条全绿（ruff / mypy / tsc 均干净），API 与生产静态构建验证通过。

- **后端**:
  - `service.py`: 新增 `delete_memo(session, memo_id)`，直接从数据库删除，无软删除或历史版本；未找到时抛出 `MemoNotFound`。
  - `router.py`: 新增 `DELETE /api/memos/{memo_id}` 路由，成功返回 204 No Content，不存在时返回 404。
  - `tests/test_memo_api.py`: 在主接缝上补充覆盖删除单条 Memo、删除后列表与详情均不再返回、删除不存在 ID 返回 404、删除不影响其余记录的倒序排序，以及删除后重启服务持久性校验。
- **前端**:
  - `shared/api.ts`: 支持 204 响应码并返回 `undefined`，新增导出 `del` 方法。
  - `memo/api.ts`: 新增导出 `deleteMemo(id)`。
  - `MemoItem.tsx`: 在展开状态的卡片头部增加「删除」按钮（支持键盘与鼠标操作），通过 `window.confirm` 进行二次确认防误触，展示「删除中…」并处理失败提示。
  - `MemoList.tsx` / `MemoPage.tsx`: 删除后就地从列表状态过滤移除，页面刷新后因持久化删除依然不在。
- **文档同步**:
  - `docs/running.md`: 更新手工验证清单，加入删除操作校验；更新数据清理说明，说明可以直接在卡片头部点「删除」。


---

**Review 后的修正**

**删不掉图片文件时,删除请求以前返回 500,但 memo 其实已经删掉了。** `delete_memo` 先 `commit()` 再 `rmtree()`,Windows 上截图被看图软件占着就会走到这条路:界面显示「删除失败」、那一行还留着,刷新之后才发现真没了 —— 而且残留目录会被下一条复用同 id 的 memo 继承(详见票 04)。

现在删不掉文件不算失败:memo 那一行已经没了,回一个错误等于撒谎。残留目录在 id 复用时由创建流程收走。
