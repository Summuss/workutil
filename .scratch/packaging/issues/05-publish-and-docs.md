# 05: 发布渠道与文档

**What to build:** 把包送到工作机的那条路,以及所有需要跟着改的文档。

工作机**能匿名访问 GitHub 但不能登录账号**,所以渠道是 GitHub Release 的 zip 资产 —— 这要求**仓库是 public**。

> ✅ **公开仓库已确认,仓库已建并推送**(`Summuss/workutil`)。发布内容扫过:没有邮箱、密钥或公司标识。`docs/running.md` 里的 `summus@192.168.3.3` 已改成占位符 —— 但注意**历史提交里仍然有它**,那是 RFC1918 私有网段地址,出了局域网没有意义,不值得为它重写历史(见下方 Notes)。

剩下的是发 release:`make package` 的产物作为资产挂上去,版本号取 `pyproject.toml`。

文档这边,`requirements.md §6` 那条「工作机能否自由安装软件」**已经关掉了**(实测:工作机可在任意位置执行程序,而便携包本来也绕开了「安装」),§3 与 §5 也跟着更新过。这一条只需复核它们与最终实现一致。

**Blocked by:** 04

**Status:** ready-for-agent

- [x] `running.md` 里的 `summus@192.168.3.3` 改成占位符
- [x] 建 public 仓库并推送(`Summuss/workutil`)
- [ ] 发第一个 release,`make package` 的产物作为资产
- [x] `requirements.md §6` 关掉「工作机能否装软件」那条,写上实测结论
- [x] `requirements.md §5` 的「部署简单」补上现在的实际形态(解压即用)
- [ ] `design.md` 新增打包章节:包的形状、为什么不用 PyInstaller、`frontend_dist` 三级查找、`open_app_window` 是平台层第三个动词
- [ ] `design.md §7` 的「在服务器上验不了」补第二条:便携包能否跑起来、app 窗口长什么样
- [ ] `running.md §C` 整节重写:下载 → **解压前右键 zip 解除锁定** → 解压 → 双击;以及升级就是删掉旧文件夹解压新的、数据在 `%LOCALAPPDATA%` 不受影响
- [ ] `running.md` 补 Edge「安装为应用」的步骤,以及在哪儿打开开机自启
- [ ] `running.md` 手动清单补:双击起得来、窗口有图标没有地址栏、重复双击只是把窗口拿到眼前、装成 PWA 后开始菜单里有条目、导航栏显示的版本号和下载的 zip 一致
- [ ] 复核 ADR-0009(便携包在 Linux 上组装)与 ADR-0010(UI 仍然是浏览器)—— 两条都已写好,若实现中理由有变则一并更新
- [ ] 若实现中对 spec 有偏离,在 `spec.md` 里改掉

## Notes

### 历史提交里的那个 IP

`docs/running.md` 从很早就带着 `summus@192.168.3.3`,HEAD 已经改成占位符,但**历史提交里还在**,而公开仓库公开的是整个历史。

**不重写历史**,理由:那是 RFC1918 私有网段地址,出了那台服务器所在的局域网就没有任何意义,既不可路由也不指向任何公网资产;`summus` 是本机用户名,和已经公开的 GitHub 账号同源。为它跑一趟 `git filter-repo` 要重写全部提交哈希,而这个仓库的提交历史本身就是设计文档的一部分(每条 commit message 都记着当时的推导),代价远大于收益。

真正的纪律是往后:**任何真实主机名、内网地址、公司标识都不进仓库**,`running.md` 里一律用占位符。
