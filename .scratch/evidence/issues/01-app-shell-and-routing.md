# 01: 应用外壳与路由

**What to build:** M2 之后工具不止一个功能了,需要一层顶部导航。引入 react-router,`/` 是 memo,`/evidence` 是 evidence 列表。

**这张 ticket 是整个 M2 里唯一会碰 memo 的地方,而它有一条不能破的约束**:requirements.md F1 的核心卖点是「打开工具时光标已经在输入框里,零导航点击」。加了路由之后 `/` 必须**直接就是 memo 页、输入框已聚焦**,不能多一次跳转、不能先闪一下导航再渲染。这条卖点是 F1 存在的理由,不能被一次基础设施改造顺手弄丢。

选 react-router 而不是自己用 useState 切 tab:evidence 有三级导航(列表 → 某份 → Case),自己做等于手写一遍浏览历史;M3/M4 还有三个功能要进来。

**Blocked by:** —

**Status:** done

- [x] 引入 react-router,`/` → memo,`/evidence` → evidence 列表(本 ticket 里先放一个空壳页)
- [x] 顶部有导航,能在两个功能间切换,当前位置可辨
- [x] **打开 `/` 时输入框已经聚焦**,和加路由之前完全一样
- [x] 浏览器前进后退在两个页面间正常工作
- [x] `pnpm build`(含 `tsc --noEmit`)通过

## Comments

react-router 8.3.1(它要求 Node ≥ 22.22.0,服务器上是 22.22.3 —— 擦边通过,已写进 running.md;
工作机只拿 `dist/`,不受影响)。

- `App.tsx` 是路由表,`/` **直接渲染 `MemoPage`**,不是 `<Navigate>` 过去的 —— 中间任何一跳都会
  让焦点闪一下。`*` 落回 `/`。
- `AppNav.tsx` 压成一行高:导航多占的每一像素都把输入框往下推。当前位置用 `NavLink` 的
  `aria-current="page"` + 底色标出。
- `features/evidence/EvidencePage.tsx` 是空壳,ticket 03 起填内容。

### 后端也动了一处:真实路径需要 SPA 回退

原来 `main.py` 用 `StaticFiles(html=True)` 挂在 `/`,那只对目录请求返回 `index.html`。
用了真实路径路由之后,在 `/evidence` 上按 `F5` 会向后端要一个不存在的文件 —— 生产形态下
直接 404,页面打不开。这不在验收条目里,但少了它路由等于半残,所以补上:

`SinglePageApp` 覆盖 `get_response`,「像是路由路径」且没找到文件时改返回 `index.html`。
**带扩展名的路径和 `/api` 下的路径保持 404**:失效的 `<script src>` 拿到 HTML 会报成 MIME
类型错误,比 404 难查得多;fetch URL 打错也不该拿回一个页面。

这里有个坑,code review 抓出来的:`StaticFiles(html=True)` 报 miss 有**两种**方式 —— 通常抛
`HTTPException`,但只要构建产物里存在 `404.html`,它改为**返回**一个 404 响应。只 catch 异常
的写法会被静默绕过。Vite 现在不生成这个文件,但哪天有人往 `public/` 放一个,刷新就又坏了,
而且不会有测试红。两种都处理了,并且加了一条测试守着(拿掉修复它会红)。

`tests/test_ui_serving.py` 六条,走 HTTP 主接缝:`/` 出 app、`/evidence` 出 app、构建里有
`404.html` 时 `/evidence` 仍出 app、`/api/nope` 仍 404、缺失的 asset 仍 404、真实 asset 正常。
临时 dist 目录经 `conftest.workutil_at(data_dir, frontend_dist=…)` 传进去,不另起一套启动方式。
后端 63 条全绿。

### 「打开即聚焦」是怎么验的

服务器上没有浏览器,这条又恰恰是本 ticket 唯一不能破的约束,所以用 jsdom 搭了个**一次性**
的渲染检查跑了三条:`/` 首帧后 `document.activeElement` 就是那个 textarea、导航点击与
前进后退、直接深链 `/evidence`。三条都过,**然后把检查和 jsdom 依赖都删了** —— 项目刻意
不写前端自动化测试(`.scratch/memo/spec.md`),加第二个例外是要单独定的事,不该顺手夹带。
回归靠 running.md 的人工清单,已把这四条加在最前面。

生产形态的 HTTP 行为另外真跑了一遍(`make run` + curl):`/` 与 `/evidence` 都是 200 且
body 与 `dist/index.html` 逐字节相同,`/api/nope` 与缺失 asset 都是 404。

### 一个没修的已知回归

加了路由之后,**输入框里有半条没存的 memo 时点「Evidence」,那半条就没了** —— `MemoPage`
被卸载,草稿在组件 state 里。加路由之前没有「切走」这个动作,所以这是本次引入的。

没在这张 ticket 里修:修法是把草稿存起来(`sessionStorage` 或提到路由之上),那等于给 Memo
加一个「草稿持久化」的行为 —— 它会顺带改变 `F5` 之后的表现,是个产品决定,不该夹在一次基础
设施改造里顺手做掉。留给使用中判断值不值一张 ticket。
