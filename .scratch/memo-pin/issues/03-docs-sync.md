# 03: 文档与手动清单同步

**What to build:** `CONTEXT.md` 的「置顶」词条、`requirements.md` F1、`design.md` F1、`docs/adr/0008-memo-can-be-pinned-but-not-categorised.md` 都是写 spec 时**先行**写好的 —— 核对它们与实际实现一致,并补 `docs/running.md` 的手动清单。

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] 核对 `CONTEXT.md` 的「置顶」词条与实际行为一致(尤其「不是分类」这条界限没有在实现中被越过)
- [ ] 核对 ADR-0008 的 Consequences 与实际实现一致
- [ ] 核对 `design.md` F1 里 `pinned_at` 那两条与实际查询形状一致
- [ ] `running.md` 补:钉一条 memo,它跳到顶部并带分隔标题
- [ ] `running.md` 补:钉第二条,它排在第一条**上面**(最近钉的在最上)
- [ ] `running.md` 补:取消置顶,它回到时间倒序里的原位置
- [ ] `running.md` 补:钉一条很旧的 memo(旧到不在列表里),它稳定出现在顶部
- [ ] `running.md` 补:开始搜索后置顶区消失,结果是纯搜索结果
- [ ] `running.md` 补:置顶一条 memo 后,它的「修改于」**没有**出现
- [ ] `running.md` 补:日语界面下置顶区标题与按钮提示是日语
- [ ] 若实现中对 spec 做了偏离,在 `spec.md` 里改掉
