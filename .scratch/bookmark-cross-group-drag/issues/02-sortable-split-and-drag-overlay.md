# 02: `shared/sortable` 拆分 + 引入 DragOverlay

**What to build:** `shared/sortable/index.tsx` 现在的 `SortableList` 把 `DndContext` 和 `SortableContext` 打包在一起,每个列表各带一个 context —— 跨列表拖拽在这个结构下不可能。拆成两种用法:

- **自带 context 的 `SortableList`**(现状):Todo、Evidence 用例、Evidence Block 三处继续用,零改动
- **容器 + 子列表**:一个只提供 `DndContext` 的外层,配上纯 `SortableContext` 的子列表,给 ticket 03 的书签页用

同时**引入 `DragOverlay`**。这不是可选项:`fixed-layout` 之后内容区是 `overflow` 滚动容器,而现在的拖拽是「原地半透明 + transform 位移」,拖出容器边缘**会被裁掉**。`DragOverlay` 渲染在 portal 里,不受祖先 overflow 影响。

**这会统一改变全部五处已有拖拽的观感**:被拖的东西变成跟随光标的浮层,原位留一个占位空槽。这是升级不是回归,但每一处都要手动看过。

**Blocked by:** 无(可与 01 并行)

**Status:** resolved

- [x] `shared/sortable` 拆出「自带 context」与「容器 + 子列表」两种用法,公用同一套 sensor 配置
- [x] 引入 `DragOverlay`,被拖元素渲染为跟随光标的浮层,原位留占位空槽
- [x] 拖拽元素在滚动容器边缘**不再被裁剪**
- [x] Todo 排序:拖拽与键盘拖拽均正常
- [x] Evidence 用例标签排序(横向):拖拽与键盘拖拽均正常
- [x] Evidence Block 排序:拖拽与键盘拖拽均正常
- [x] 书签分组排序、组内书签排序:拖拽与键盘拖拽均正常(此时仍不跨组)
- [x] 「置顶 / 置底」按钮不受影响
- [x] `make check` 通过
