# 04: 后端错误信息 code 化

**What to build:** 后端自定义异常从「裸字符串消息」改成带 `code` 字段,前端按 `code` 查语言包渲染,而不是原样显示后端传来的文本。

现状(已核实):`backend/app/modules/{memo,todo,bookmark,evidence}/service.py` 的自定义异常直接拿中文(个别是英文,如 memo 模块)提示字符串当消息,`router.py` 用 `raise HTTPException(status, str(err))` 透传,前端 `shared/api.ts` 的 `refusalFrom`(20-28 行)把 `detail` 字段原样显示给用户,中间没有任何 key 层。这意味着不做这张票的话,日语模式下会不定期弹出中文错误框 —— 这是这次范围比最初设想扩大的地方(spec.md「为什么后端错误信息被拉进了这次范围」)。

**只给「预期内的用户可纠正错误」分配 code**(比如 `EmptyTitle`、`PathDoesNotExist` 这类 4xx 校验失败)。**非预期的异常(500)不逐个分类**,统一返回一条通用的、已翻译的「未知错误」文案 —— 那些是 bug,不是需要打磨措辞的用户提示。

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] 遍历 `backend/app/modules/{memo,todo,bookmark,evidence}/service.py` 的自定义异常,统一带一个 `code` 字段(如 `todo.empty_title`)
- [ ] 对应的 `router.py` 把 `code` 放进 4xx 响应体,不再只回一句拼好的中文 `detail`
- [ ] `frontend/src/shared/api.ts` 的 `refusalFrom` 按 `code` 查语言包渲染;网络失败 / 载入失败等既有的前端侧兜底文案(`shared/api.ts:36`、`shared/useLoad.ts:41`)也一并接入 `t()`
- [ ] `zh.json`/`ja.json` 补齐这些错误 key 的翻译
- [ ] 未分类的非预期异常仍返回一条通用的、已翻译的「未知错误」文案
- [ ] 主接缝测试:至少一个已知校验失败(如提交空标题的 Todo)断言响应体带的是 `code` 而不是裸中文字符串
- [ ] 切到日语触发同一个失败操作,提示是日语;切回中文,提示是中文
- [ ] key 对齐测试仍然通过
- [ ] `make check` 与 `pnpm build` 通过
