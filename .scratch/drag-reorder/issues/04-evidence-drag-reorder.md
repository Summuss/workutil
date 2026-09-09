# 04: Evidence(Case + Block)改为拖拽排序

**What to build:** 同样用 02 的可复用 sortable 包装,把 `CaseTabs`(Case 顺序)和 `BlockCard`(Case 内 Block 顺序)从按钮改成拖拽。去掉「上/下」、保留「置顶/置底」、加拖拽把手。

拖拽范围严格保持不变:Case 只能在同一个 Evidence 内排序,Block 只能在**同一个 Case 内**排序,不做跨 Case 拖拽。

**Blocked by:** 02

**Status:** resolved

- [x] `CaseTabs`:去掉 Case 的「上/下」按钮,保留「置顶/置底」,加拖拽把手,Case 间可拖拽排序
- [x] `BlockCard`:去掉 Block 的「上/下」按钮,保留「置顶/置底」,加拖拽把手,**仅同 Case 内**可拖拽排序
- [x] 键盘拖拽可用(复用 02 的 sensor 配置)
- [x] 松手时调用 ticket 01 的绝对位置接口;本地乐观更新,失败时回滚
- [x] `pnpm build`/`tsc` 通过;手动验证 Case 间拖拽、Block 组内拖拽、跨 Case 拖拽确实不可行
