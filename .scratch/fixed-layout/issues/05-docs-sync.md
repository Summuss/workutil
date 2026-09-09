# 05: 文档与手动清单同步

**What to build:** `docs/requirements.md`(§5「界面稳定」)、`docs/design.md` §3.4、`docs/adr/0007-fixed-viewport-shell.md` 是在写 spec 时**先行**写好的 —— 这一条负责回头核对它们与实际做出来的东西一致,并把 `docs/running.md` 的手动清单补上。

UI 回归在本仓库只能靠手动(design.md §9),而这次改的是**每一个页面的布局**,清单不补等于这次改动没有回归网。

**Blocked by:** 01, 02, 03, 04

**Status:** ready-for-agent

- [ ] 核对 `design.md` §3.4 描述的固定区划分与实际实现一致(尤其是 Evidence 详情的底部粘贴框)
- [ ] 核对 ADR-0007 的 Consequences 与实际踩到的坑一致;实现中发现新的连带后果就补进去
- [ ] `running.md` 补:七个页面都不出现窗口滚动条,内容超长时滚动条在内容区
- [ ] `running.md` 补:导航切页时内容左右边界不变
- [ ] `running.md` 补:展开 / 折叠一条带截图的 memo,页面框架不动
- [ ] `running.md` 补:点截图开灯箱,`Esc` / 点背景 / 关闭按钮三种方式都能关
- [ ] `running.md` 补:Evidence 来回切换用例,内容区高度不变、滚动位置回到顶部
- [ ] `running.md` 补:Evidence 里连续粘 3 张截图,粘贴框始终可见
- [ ] `running.md` 补:一键打开一组带失效项的书签,提示条出现时列表不位移
- [ ] 若实现中对 spec 做了偏离,在 `spec.md` 里改掉,不留下与代码不符的描述
