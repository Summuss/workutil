# 01: 卡片里的图整张缩进一屏

**Status:** resolved

**Blocked by:** 无

**What to build:** `BlockCard` 的 image Block 加一个**跟着可视区域走**的高度上限,让一整张卡片(小标题行 + 图)能同时落在 block 列表的视野里。理由与被推翻的旧决定见 [spec](../spec.md)。

现在的样式是 `max-w-full self-start rounded-md` + 一道 border(`BlockCard.tsx` 的 image 分支)。宽度上限不变,再加一个高度上限,两个一起作用、等比缩、不放大。

- 「一屏」= `CaseBlocks` 里那个滚动容器(`scrollContainerRef`)的可视高度,减去卡片头部、上下内边距和一点呼吸余量。具体减多少按实际渲染量,目标是卡片顶边和底边都在视野里。
- 推荐做法是把那个滚动容器设为 size 查询容器(`container-type: size`),图上写 `max-height: calc(100cqh - <卡片自身的高度>)`。它是 `flex-1 min-h-0`,尺寸由父级决定、不依赖内容,满足 size containment 的前提。窗口缩放、memo 侧栏开合都会自动跟上,不需要 JS。真跑不通再退到 `ResizeObserver` 写一个 CSS 变量。
- **不裁剪、不藏任何一部分**:是 `max-height` 让整张等比缩小,不是 `overflow: hidden` 截掉。长图会变成窄窄一条,这是知情的。
- 点击开灯箱、加载失败不开灯箱、alt 文字,都维持现状。
- 不动 memo,不动 `shared/Lightbox`(那是 02)。

**留意:** `CaseBlocks` 里「加完一段滚到它」那段逻辑(等 `<img>` 的 `load` 再 `scrollIntoView({ block: "end" })`)不需要改,但要验证它在新上限下还落在对的地方。

- [x] 在小窗口(模拟笔记本,例如 1366×768)里,一张 1920×1080 的截图整张出现在一屏内,卡片的小标题行也在视野里
- [x] 一张 1920×6000 的长截图整张出现在一屏内(窄条),点它照样开灯箱
- [x] 比上限小的图原样大小显示,不被放大
- [ ] 拖动窗口改变高度、开合 memo 侧栏(`Ctrl+M`),图的大小实时跟着变
- [ ] 很宽的截图仍然缩到卡片宽度,不出横向滚动条
- [ ] 连续粘 3 张截图,每次都滚到新加的那张,整张卡片可见
- [ ] 拖动一个图片 Block 排序,`DragOverlay` 里的影子不超过一屏
- [x] `docs/running.md` 的「Evidence(M2,图片 Block)」一节补上前三条;「很宽的截图」那行保留
- [x] `pnpm build` / `tsc` 通过

## Comments

由 agy 实现,host 复核。无头 Chromium 实测(测试图 1920×1080 / 1920×6000 / 300×200):

- 1366×650 视口:block 列表可视高度 290px,三张卡片都是 258px,整张卡片落在视野内;普通图显示为 357×202,长图 66×202,小图原样。
- 1920×1000 视口:可视高度 640px,卡片 608px;普通图 979×552,小图仍原样不放大。
- 笔记本上可视区域本来就只有 300px 上下,普通截图在卡片上会很小 —— 这是 spec 里知情的代价,看清靠 02/03 的灯箱。

窗口缩放 / 侧栏开合 / 连续粘贴 / DragOverlay 几项未在浏览器里逐条点过,留给人工复核。`DragOverlay` 被 portal 到 `body`,没有查询容器祖先时 `cqh` 按规范回退到 `svh`,影子不会超过一屏。
