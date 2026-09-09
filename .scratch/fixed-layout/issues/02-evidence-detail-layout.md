# 02: Evidence 详情页的三段式布局与用例切换

**What to build:** 把 `EvidenceDetailPage` 做成「头固定 + 中间滚 + 底固定」三段,并消掉切换用例时那两跳(先塌成一行 loading、再撑到新用例的高度)。

头是返回/标题/导出那一行加用例标签栏,底是 `CaseBlocks` 末尾那个新增 Block 的 `BlockTextArea` —— 它**移到固定底部**,不再跟着 block 列表滚。理由是 requirements.md §4 F5 的验收要点「连续粘贴多张截图,过程中不需要切换到其他软件」:框常驻,粘完新块出现在它上方。代价是它和「追加到末尾」的空间语义脱钩,已在 spec 里接受。

`CaseBlocks` 的 loading 分支从「一行居中文字」换成**与内容区等高的骨架占位**,加载中不改变布局高度。`key={selectedId}` 的重挂载保持不变(它保证不会看到上一个用例的内容),但滚动容器在切换后回到顶部。不缓存已读过的用例。

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] `EvidenceDetailPage`:头部(返回/标题/导出 + `CaseTabs`)固定,不参与滚动
- [ ] `CaseBlocks` 的 block 列表是唯一的滚动区
- [ ] `BlockTextArea`(新增 Block)固定在底部,始终可见
- [ ] 粘贴一张截图后,新 block 出现在列表末尾,输入框仍在原地、仍可继续粘
- [ ] `CaseBlocks` 的 loading 分支换成等高骨架占位,切换用例时内容区**高度不变**
- [ ] 切换用例后滚动位置回到顶部
- [ ] 不缓存用例内容(切走再切回仍然重新拉取)
- [ ] 用例为空、加载失败两种状态也不改变内容区高度
- [ ] 导出按钮在无用例时仍然是禁用的(现有行为不能被布局改动带坏)
- [ ] `make check` 通过
