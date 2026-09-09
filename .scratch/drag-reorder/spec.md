# Spec: 排序交互从按钮改为拖拽

Status: ready-for-agent

## Problem Statement

现有 Todo、书签(分组 + 组内书签项)、Evidence(Case + Block)共五处列表用「上/下/置顶/置底」四个按钮排序,这是 `docs/design.md` 里明确记录过的决定 —— 拖拽的依赖成本和键盘可访问性成本不值得。用久了发现「上/下」单步移动在离目标位置远时格外繁琐,想直接拖动元素到目标位置。

## Solution

保留「置顶/置底」按钮做远距离跳转,「上/下」单步按钮用拖拽取代。拖拽用 dnd-kit —— 它自带键盘拖拽,正好补上当初放弃拖拽时最主要的可访问性顾虑。每行加一个专门的拖拽把手图标,而不是整行可拖,避免和行内其他按钮/链接打架。范围严格保持不变:仍是同列表/同分组内排序,不做跨组、跨 Case 拖拽;Todo 仍只有未完成项可排序。后端 `core/ordering.py` 的共享 `Move`/`reorder` 扩展出「绝对目标位置」能力,一次拖拽一次请求,并移除不再使用的 `up`/`down` 两个方向值。

## Domain Model

不引入新领域概念。`Ordered` 契约不变(order 是从 0 开始的连续整数,变更时整体重编号),只是移动操作的**参数**从「方向」变成「方向(仅 top/bottom)或绝对目标位置」。

## User Stories

1. 作为使用者,我希望能直接拖动一条 Todo/书签/Case/Block 到目标位置,而不是反复点「上移」很多下。
2. 作为使用者,我希望列表很长、要挪到很远的位置时,仍然可以用「置顶/置底」一步到位,不需要靠拖拽滑很远。
3. 作为使用者,我希望拖拽只在按住把手时才发生,不会因为点到行内其他按钮(编辑、删除、勾选完成等)而误触发。
4. 作为使用者,我希望键盘也能完成排序,这样这个交互不会比原来的按钮更难用键盘操作。
5. 作为使用者,我希望书签只能在同一个分组内拖拽排序、Block 只能在同一个 Case 内拖拽排序 —— 和现在按钮排序的范围一致,不会因为改成拖拽而多出「拖到别的组/别的 Case」这种新行为。

## Implementation Decisions

### 范围

- 五处全部转:Todo、BookmarkGroup、Bookmark(组内)、EvidenceCase、EvidenceBlock —— 它们本来就共享同一套后端机制(`core/ordering.py`),只改一部分会让实现风格分裂,以后维护心智负担更大。
- 保留「置顶/置底」按钮(远距离跳转,拖拽体验差);去掉「上/下」单步按钮(拖拽替代)。
- 拖拽范围与现有按钮完全一致,不扩展能力:仍是**同列表/同分组内**排序,不做跨组、跨 Case 拖拽;Todo 仍只有未完成且列表长度 > 1 的项可排序,与现在一致。

### 前端

- 引入 dnd-kit(`@dnd-kit/core` + `@dnd-kit/sortable`),项目目前零拖拽依赖。
- 每行加专门的拖拽把手图标(新增到 `shared/icons.tsx`,沿用现有 feather 描边风格),只有按住把手才能拖动 —— 这几处行内都还有其他可点击元素(checkbox、编辑/删除、链接等),整行可拖会冲突。
- 启用 dnd-kit 的键盘 sensor(空格拾起、方向键移动、空格放下),这是选 dnd-kit 而不是手写实现的主要理由,回应 design.md 当初放弃拖拽的可访问性顾虑。
- 五处共享同一套 sortable 包装,不各自重新接线 dnd-kit。

### 后端

- `core/ordering.py` 的 `Move`/`reorder` 扩展出「绝对目标位置」能力(在现有 `top`/`bottom` 之外新增)。`order` 已经是从 0 开始的连续整数,`top`/`bottom` 本来就是走「弹出-插入-整体重编号」这条路径跳到边界 —— 这是纯新增能力,不需要数据迁移。
- 一次拖拽 = 一次 HTTP 请求,而不是把远距离拖拽拆成多次 `up`/`down` 调用(那样是多次串行请求、非原子操作)。
- 移除 `Move.UP`/`Move.DOWN` 及其分支:前端改造完后单步移动和任意位置移动都走新的绝对位置参数,这两个方向值不再有调用方。个人工具、无外部 API 消费者,不留没人调用的分支。
- 五个资源共享同一份 `ordering.py` 逻辑,这处改动是一次集中修改,不是分别改五遍。

### 接口面变化

| 端点 | 变化前 | 变化后 |
| --- | --- | --- |
| 五个 `POST .../move` 端点(Todo/BookmarkGroup/Bookmark/EvidenceCase/EvidenceBlock) | `{to: up\|down\|top\|bottom}` | `{to: top\|bottom}` 或携带目标位置的形状(具体形状由 ticket 01 定) |

## Testing Decisions

| 位置 | 测? | 理由 |
| --- | --- | --- |
| HTTP API(绝对位置 move) | ✅ 主接缝 | 新能力的正确性:移到中间位置、边界情况、重编号 |
| 前端拖拽交互 | ❌ | 沿用本仓库一贯做法 —— UI 交互不写自动化测试,手动跑 `/run` 验证 |

## Out of Scope

| 项目 | 说明 |
| --- | --- |
| 跨组 / 跨 Case 拖拽 | 能力扩展,超出「把按钮换成拖拽」这个范围,以后单独提 |
| 触屏专门优化 | 两台目标机器(Windows 工作机 + macOS 私人机)都是桌面端,dnd-kit 默认的 PointerSensor 已覆盖鼠标场景 |
| 拖拽视觉效果定制(阴影、动画曲线等) | 用 dnd-kit 默认表现,不是这次的重点 |

## Further Notes

### 这是对已有书面决定的反转

`docs/design.md`、`.scratch/evidence/spec.md`、`.scratch/bookmark/spec.md`、`.scratch/todo/spec.md` 都明确写过「不做拖拽」,理由是「依赖成本 + 键盘可访问性成本不值得」。dnd-kit 自带键盘拖拽,这笔账变了,所以这次反转是有理由的,不是随手改。ticket 05 负责把这些文档同步更新,并在旧的、已关闭的 ticket(`evidence/issues/04-text-block.md`、`bookmark/issues/03-groups.md`、`todo/issues/02-manual-ordering.md`)里补一条指向本目录的说明,而不是重写它们的历史记录。

### 相关文档

- `docs/design.md`(Evidence 排序段落)
- `.scratch/evidence/spec.md`、`.scratch/bookmark/spec.md`、`.scratch/todo/spec.md`
