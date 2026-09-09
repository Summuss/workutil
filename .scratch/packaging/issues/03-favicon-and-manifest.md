# 03: favicon、web manifest 与 PWA 可安装

**What to build:** 前端现在**连 favicon 都没有** —— `frontend/` 下没有 `public/` 目录,`index.html` 里没有 `<link rel="icon">`。所以标签页上是个空白图标,而「找到 workutil 那个标签页」正是 `design.md §1` 认定的最大产品风险的一部分。

补三样东西:图标、manifest、以及 `index.html` 里的引用。做完之后:

- app 模式窗口的任务栏图标有了(否则是个空白方块)
- Edge 能看到「将此站点作为应用安装」,装完得到开始菜单条目、桌面快捷方式、**以及 Edge 自带的开机自启开关**
- `127.0.0.1` 算 secure context,装 PWA **不需要 HTTPS**

**这一条整个可以在 Linux 服务器上验证** —— 纯前端,浏览器里就看得见,是本 spec 里唯一不用碰目标机的部分。

图标自己画一个极简的,不引第三方图标库:它要在 16px 的任务栏上认得出来,复杂图案没有意义。风格跟现有的 feather 描边 icon 和 `--accent` 色调一致。

**Blocked by:** 无(可与 01/02 并行)

**Status:** ready-for-agent

- [ ] 新建 `frontend/public/`,放 favicon(SVG + ICO)与 192×192、512×512 两个 PNG
- [ ] 图标在 16px 下仍然认得出来,配色与 `--accent` 一致
- [ ] `manifest.webmanifest`:`name`、`short_name`、`icons`、`start_url: "/"`、`display: "standalone"`、`theme_color`、`background_color`
- [ ] `index.html` link 上 favicon 与 manifest
- [ ] `pnpm build` 后这些文件都在 `dist/` 里(Vite 会原样拷 `public/`)
- [ ] 后端能正确提供它们 —— `_is_a_frontend_route` 认为带扩展名的路径不是前端路由,会走 `StaticFiles`,确认 `manifest.webmanifest` 与 `.png`/`.ico` 都拿得到而不是被喂了 `index.html`
- [ ] 浏览器标签页显示图标(服务器上验)
- [ ] Edge / Chrome 的菜单里出现「安装此站点为应用」(服务器上验)
- [ ] `make check` 通过
