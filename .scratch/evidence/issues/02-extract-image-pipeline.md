# 02: 图片链路下沉到 core/images.py

**What to build:** 纯重构,不加任何功能。把 `_decode_image` / `_save_images` / `count_images` / `_discard_images` 从 `backend/app/modules/memo/service.py` 提到 `backend/app/core/images.py`,参数化「图片目录 + URL 前缀」,让 memo 和后面的 evidence 都能用。

ADR-0001 说 Memo 与 Evidence「共享机制、不共享概念」—— 这张 ticket 就是那句话的落点。注意共享的只有这条技术链路,不要顺手抽象出一个「有图片的东西」的公共基类。

前端的 `ImageUpload` 类型现在在 `frontend/src/features/memo/types.ts`,而 `shared/useImageAttachments.ts` 反向 import 了它,一并挪到 `shared/`。

**验收就是既有测试全绿** —— 行为一个字节都不该变。

**Blocked by:** —

**Status:** done

- [x] `core/images.py` 提供解码、落盘(含临时引用改写)、计数、清理,接受「目录 + URL 前缀」作为参数
- [x] `memo/service.py` 改为调用它,memo 的行为完全不变
- [x] 现有后端测试全绿,一条都不用改(改了就说明行为变了)
- [x] `ImageUpload` 类型移到 `frontend/src/shared/`,`useImageAttachments` 不再 import `features/memo/`
- [x] ruff / mypy / tsc 干净

## Comments

`core/images.py` 是四个自由函数加一个 wire model:`count(directory)` / `discard(directory)` /
`save_and_link(directory, url_prefix, body, uploads)`,外加 `ImageUpload`、`InvalidImage`、
`IMAGE_EXTENSIONS`、`MAX_IMAGE_BYTES`。没有基类,没有「有图片的东西」——
ticket 那句警告照做了。

**「哪个目录属于谁」不在 core 里**,留在各自模块:`memo/service.py` 的 `memo_images_dir()`
和 `_memo_images_url()` 是这一对唯一的定义处。Evidence 到时候自己出一对,`core` 不需要知道
有几种主人。

### 怎么证明行为没变

除了既有测试,另外拿**生成的 OpenAPI schema 逐字节 diff**(HEAD 的 worktree vs 现在):
447 行里只有一处不同 —— `ImageUpload` 的 docstring 从「memo」改成了「text / the thing」,
因为这个 model 现在不属于 memo 了。schema 结构、字段名、路由、状态码全同。

### 动了一行既有测试

`tests/test_memo_api.py` 里 `from app.modules.memo.service import MAX_IMAGE_BYTES` 改成
`from app.core.images import ...`。断言一个字没动。

本可以在 `service.py` 里留个 re-export 把这行也保住,但那是为了满足字面而留的死代码 ——
25MB 上限现在是共享链路的规则,不是 memo 的。所以选择改这一行,并且写在这里,不让它悄悄过去。

### 顺手收掉的两处

- `router.py` 的 `get_memo_image` 原本自己拼 `images_dir / str(memo_id) / filename`。
  既然这张 ticket 的意义就是把「目录长什么样」收成一处,它也改走 `memo_images_dir()`,
  否则新的 helper 一出生就已经有个竞争者了。路径穿越那道校验没动。
- `docs/design.md` §6 F5 里「图片链路要先下沉」那段写的是待办,改成了已完成的实际形态。

前端:`ImageUpload` 移到 `shared/images.ts`,`useImageAttachments` 不再反向 import
`features/memo/`。
