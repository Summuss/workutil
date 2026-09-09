# 03: 加完 Block 之后滚到它那里

**What to build:** `CaseBlocks` 里,`setBlocks` 之后把新加的最后一个 Block 滚进视野。

**病根是「看不见」,不是「没被告知」。** 新 Block 追加在列表末尾(`setBlocks([...blocks, added])`),而滚动容器停在哪里完全由人决定 —— 停在中间时粘一张图,它落在屏幕外,画面上什么都没变。

**所以这里刻意不加 toast。** 滚过去同时回答了「成了吗」和「在哪」两个问题,而 toast 只回答前一个,还要在固定外壳(design.md §3.4)里额外操心它会不会推动布局。

**做法:**

- `scrollIntoView({ block: "nearest" })`,滚到**最后一个**新 Block(一次粘 3 张图滚到第 3 张,途中经过的自然看得见)。
- 三种 kind 都滚:文字(`handleAdd`)、图片(`handleImages`)、表格(`handleTable`)。
- **不用 `smooth`** —— 连着粘几张图时动画会互相打断,在滚动容器里看起来像卡顿。
- `block: "nearest"` 意味着**已经在视野里时它本身就不动**,不需要写额外的可见性判断。
- 注意时机:`setBlocks` 之后 DOM 还没更新,要等一次渲染(`useEffect` 盯着新 Block 的 id,或 `requestAnimationFrame`),否则拿不到那个节点。

**表格那条既有提示不动。** 「识别为表格,8 行 5 列 · 改为纯文字」照常出现 —— 它本来就兼着「刚才那一下确实进去了」的职责(design.md §6 F5),而且它是一个**可点的更正入口**,不是单纯的通知。

**Blocked by:** 无

**Status:** resolved

- [x] 加文字 Block 后滚到它
- [x] 加图片 Block 后滚到**最后一张**;一次粘 3 张只滚一次
- [x] 粘表格后滚到它,且「识别为表格」提示照常出现、行为不变
- [x] 新 Block 已经在视野里时**画面不动**(`block: "nearest"` 的自然结果,不要额外写判断)
- [x] 不使用 `smooth`
- [x] 切换 Case 时滚回顶部的既有行为不受影响(`useEffect` 里那个 `scrollTo({ top: 0 })`)
- [x] `pnpm build` / `tsc` 通过;手动验证「停在列表中间粘一张图」

