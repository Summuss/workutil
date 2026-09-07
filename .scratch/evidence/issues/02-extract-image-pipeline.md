# 02: 图片链路下沉到 core/images.py

**What to build:** 纯重构,不加任何功能。把 `_decode_image` / `_save_images` / `count_images` / `_discard_images` 从 `backend/app/modules/memo/service.py` 提到 `backend/app/core/images.py`,参数化「图片目录 + URL 前缀」,让 memo 和后面的 evidence 都能用。

ADR-0001 说 Memo 与 Evidence「共享机制、不共享概念」—— 这张 ticket 就是那句话的落点。注意共享的只有这条技术链路,不要顺手抽象出一个「有图片的东西」的公共基类。

前端的 `ImageUpload` 类型现在在 `frontend/src/features/memo/types.ts`,而 `shared/useImageAttachments.ts` 反向 import 了它,一并挪到 `shared/`。

**验收就是既有测试全绿** —— 行为一个字节都不该变。

**Blocked by:** —

**Status:** ready-for-agent

- [ ] `core/images.py` 提供解码、落盘(含临时引用改写)、计数、清理,接受「目录 + URL 前缀」作为参数
- [ ] `memo/service.py` 改为调用它,memo 的行为完全不变
- [ ] 现有后端测试全绿,一条都不用改(改了就说明行为变了)
- [ ] `ImageUpload` 类型移到 `frontend/src/shared/`,`useImageAttachments` 不再 import `features/memo/`
- [ ] ruff / mypy / tsc 干净
