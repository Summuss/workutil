# workutil

一个自用的本地开发效率工具,把日常开发中高频而琐碎的动作收进同一个地方。

## 怎么跑起来

**→ [docs/running.md](docs/running.md)** —— 开发、验收、在工作机上使用,三个场景的具体步骤。

最短路径,在服务器上:

```sh
make install
make build && make run     # 然后 ssh -L 8765:127.0.0.1:8765 过去看
```

服务只监听 `127.0.0.1`,所以从 macOS 访问要走 SSH 端口转发。

## 文档

| 文件 | 内容 |
| --- | --- |
| [docs/requirements.md](docs/requirements.md) | 要做什么、为什么。没有技术细节 |
| [docs/design.md](docs/design.md) | 怎么实现:架构、选型、模块划分、里程碑 |
| [docs/running.md](docs/running.md) | 怎么启动、怎么验收、数据在哪 |
| [CONTEXT.md](CONTEXT.md) | 术语表 —— 这个代码库该用哪些词 |
| [docs/adr/](docs/adr/) | 关键决定及其理由 |
| [.scratch/](.scratch/) | 功能规格与实现票 |
