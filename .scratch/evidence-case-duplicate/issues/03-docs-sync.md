# 03: 文档与手动清单同步

**What to build:** 核对 `requirements.md` F5 与 `design.md` F5 里先行写好的描述与实际实现一致,并补 `docs/running.md` 的手动清单。

清单里那条**「删掉副本之后原用例的截图还在」必须手动也走一遍** —— 后端测试守着它,但这是唯一会造成不可逆数据损失的路径,值得在真实数据目录上看一眼文件确实还在。

**Blocked by:** 02

**Status:** resolved

- [x] 核对 `design.md` F5 里复制用例那条与实际接口、命名规则一致
- [x] `running.md` 补:复制一个有文字 / 图片 / 表格三种 Block 的用例,副本逐段一致
- [x] `running.md` 补:复制后自动切过去,标签处于重命名状态且名字已全选
- [x] `running.md` 补:`Esc` 不会撤销复制
- [x] `running.md` 补:改成一个已存在的编号会被拒
- [x] `running.md` 补:新用例紧跟原用例,不在末尾
- [x] `running.md` 补:**删掉副本,去 `images/evidence/<id>/` 看原用例的图片文件仍在**
- [x] `running.md` 补:复制后导出 Excel,两个 sheet 内容相同、图片都在、位置正确
- [x] `running.md` 补:日语界面下复制按钮的提示与错误文案是日语
- [x] 若实现中对 spec 做了偏离,在 `spec.md` 里改掉
