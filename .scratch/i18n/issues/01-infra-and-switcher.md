# 01: i18n 基础设施与语言切换器

**What to build:** 一个自研极简 i18n 机制(`t()` + Context + 语言包),导航栏语言开关,以及默认语言探测与持久化。这一步不翻译任何现有页面文案,只把机制立起来 —— 后面几张票只管往里加 key。

`frontend/src/shared/i18n/` 下放 `zh.json`、`ja.json` 两个语言包和一个 `t(key)` 函数 + React Context(当前语言、`setLanguage`)。**不引入 react-i18next** —— 现在的规模不需要复数规则、插值、命名空间这些库要解决的问题(design.md §6 F6)。

**默认语言按 `navigator.language` 探测**(匹配 `zh`/`ja` 前缀,都不是则兜底 `zh`),手动切换后的选择存 `localStorage` 并覆盖探测结果。**不做后端接口、不建 Settings 页面** —— 语言开关是导航栏(`AppNav.tsx`)里的一个下拉,和「两台机器数据各自独立」的既有架构一致,偏好只留在这台机器的浏览器里。

`frontend/index.html` 现在硬编码 `<html lang="zh">`,改成跟随当前语言运行时更新。`shared/time.ts` 里硬编码的 `toLocaleString("zh-CN", ...)` 也改成读当前语言(`zh-CN` / `ja-JP`)—— 这不是翻译,只是换一个参数。

**查不到的 key 直接渲染 key 本身**(如 `[nav.todo]`),不做静默 fallback —— 这是留给自己的漏翻信号。同时把「`zh.json` 与 `ja.json` 的 key 集合必须完全一致」这条规则落成一个测试,现在语言包里 key 还很少(导航栏这几个),但测试机制要在这一步就跑起来、跑通,后面每张票加 key 都要过它。

**Blocked by:** —

**Status:** ready-for-agent

- [ ] `frontend/src/shared/i18n/`:`t(key)`、语言 Context/Provider、`zh.json`、`ja.json`
- [ ] 首次访问按 `navigator.language` 探测(`zh`/`ja` 前缀匹配,否则兜底 `zh`)
- [ ] 手动切换后存 `localStorage`,刷新 / 重新打开后保持
- [ ] `AppNav.tsx` 加语言下拉(中文 / 日本語),切换后界面已翻译的部分(此时只有导航栏)立即生效
- [ ] `frontend/index.html` 的 `<html lang>` 跟随当前语言更新
- [ ] 查不到的 key 直接渲染 key 本身,不 fallback 回中文
- [ ] `shared/time.ts` 的 `toLocaleString` locale 参数跟随当前语言
- [ ] key 对齐测试:断言 `zh.json` 与 `ja.json` 的 key 集合完全相同
- [ ] `make check` 与 `pnpm build` 通过
