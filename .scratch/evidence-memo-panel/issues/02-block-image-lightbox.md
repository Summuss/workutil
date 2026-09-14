# 02: evidence 的截图能点开看原图

**Status:** ready-for-agent

**Blocked by:** 无

**What to build:** `BlockCard` 的 image Block 接上 `shared/Lightbox`。

组件早就在 `shared/` 里,只是一直只接在 memo 的 Markdown 上(`shared/Markdown.tsx`)。evidence 的图现在是一个裸 `<img className="max-w-full">`,**没有任何放大的路** —— 而 03 的侧栏一开,截图只会更小。这笔代价和侧栏是同一次改动造成的,所以同一次付清。

- 照抄 `Markdown.tsx` 的接法,别新发明一套。`Esc` 关闭那条监听挂在 document 级(design.md §6 F1 记过为什么不能挂在遮罩 div 上:灯箱里没有可聚焦元素)。
- 卡片上图片的既有样式不变(`max-w-full self-start rounded-md` + 那道 border),只是多了「可点」。
- alt 维持现在的 `block.label ?? t("evidence.screenshot_alt")`。
- **不要**给 evidence 的图加高度上限缩略图 —— 那是 memo 为了解决「列表里一条撑掉一屏」做的,evidence 一屏就是一个用例,不是同一个问题。

- [ ] 点一张截图开灯箱,看到的是原图
- [ ] `Esc` 关掉;点遮罩也关掉
- [ ] 一个用例里有好几张图,点哪张开哪张
- [ ] 图片加载失败时点它不会开一个空灯箱
- [ ] memo 那边的灯箱行为一点没变
- [ ] `pnpm build` / `tsc` 通过
