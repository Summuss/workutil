# 做 evidence 时查 memo,不用离开当前用例

## 起因

制作 evidence 时经常要查 memo,但看完 memo 回来就得从 evidence 列表重新走一遍 —— 哪一份、哪个用例,全丢。

拆下来是两件事:

1. **位置丢了。** 当前 case 是组件 state,不在 URL 里。所以刷新、切去别的功能、第二天重开,都会掉回第一个用例。而 [design.md §2](../../docs/design.md) 早就写着「Evidence 有三级导航,**URL 即状态**,浏览器前进后退可用」—— 那句话目前是错的。
2. **要同时看着两样东西。** 更常见的场景是**边看边核对**(上次改的是哪个文件、报错长什么样),而不只是进去拿一段字就走。后退键解决不了这个。

两件事都做,理由和取舍见 [ADR-0013](../../docs/adr/0013-memo-panel-lives-inside-evidence.md)。

## 定下来的

- case 进 URL:`/evidence/:evidenceId/cases/:caseId`,切 tab 用 `replace`。**滚动位置不恢复。**
- evidence 详情页右侧一个**只读**的 memo 侧栏:固定 360px、不可拖、`Ctrl+M` 开合、开合状态记 localStorage、占满整个内容区高度、**挤压**而不是覆盖或推开。
- 侧栏一开截图必然变窄,所以 image Block 同时接上 `Lightbox`。
- 侧栏里**不能**编辑/删除/置顶/新建 memo,**不给**「插入到当前用例」按钮。理由都在 ADR-0013,「新建」已记进 requirements.md §7 backlog。
