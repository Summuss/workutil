# 03: Memo 图片改缩略图,点击开灯箱

**What to build:** 固定外壳治不了「单条内容自己吃掉一屏」—— 一张 1920 宽的截图在 768px 容器里能占几百像素高,展开一条带图 memo 仍然会把下面所有 memo 推出视口。这一条消掉「有图 = 高度不可预测」。

`.markdown-body img` 从 `max-width:100%; height:auto` 改成**高度上限 200px、等比缩小完整显示**(不裁剪),宽度自适应;比 200px 矮的原样显示,不放大。点击缩略图开灯箱看原图。

灯箱是 `shared/` 下的自建组件,不引第三方依赖,遮罩样式沿用 `ConvertToTodoModal`(`var(--scrim)` + `fixed inset-0 z-50`)。

**`Esc` 必须挂 document 级监听。** 不能照抄 `ConvertToTodoModal` 那个挂在遮罩 div 上的 `onKeyDown`:那里能work是因为焦点落在模态内的 input 上,而灯箱里没有可聚焦元素,键盘事件根本不会冒泡到那个 div。

Evidence 的图片 Block **不动** —— 那里是在核对要交付出去的内容,`BlockCard.tsx` 里「Shown whole」那条注释继续成立。

**Blocked by:** 01

**Status:** resolved

- [x] `.markdown-body img` 改为高度上限 200px、等比、不裁剪;矮图不放大
- [x] `shared/` 下新建灯箱组件,不引新依赖
- [x] 点缩略图打开灯箱,图片按窗口尺寸完整显示,**不放大超过原始尺寸**
- [x] 三种关闭方式都可用:`Esc`(document 级监听)、点遮罩背景、右上角关闭按钮
- [x] 关闭按钮的图标复用 `shared/icons.tsx` 已有的 `XIcon`
- [x] `MemoMarkdown` 一处改动同时覆盖 `MemoPage` 列表与 `SingleMemoPage`,不做例外
- [x] 不做多图左右切换、缩放、旋转
- [x] Evidence 的图片 Block 显示方式不变
- [x] 展开一条带 3 张截图的 memo,卡片高度与纯文字 memo 处于同一量级
- [x] 现有的 `MemoMarkdown.test.tsx`(raw HTML 安全边界)仍然通过
- [x] `make check` 通过
