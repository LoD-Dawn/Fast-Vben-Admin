# Documentation Agent Standard

本文件适用于 `docs/` 下的所有修改，并补充仓库根目录 [AGENTS.md](../AGENTS.md)。

## 1. 文档职责

- `modular-product-architecture.md` 解释产品和模块化架构原则。
- `modular-architecture-implementation.md` 记录可执行任务、当前实现证据、门禁和剩余差距。
- `module-guide.md` 指导新业务模块采用唯一接入方式。
- `adr/` 记录关键决策、状态和替代关系。
- 部署、开发、权限、监控等主题文档只描述各自领域，不复制架构事实源。

同一事实只维护一次，其他文档用链接引用。不要在 README、部署文档和 ADR 中复制易过期的测试数量、migration head 或配置清单。

## 2. ADR 治理

- Accepted ADR 不直接改写结论；变更决策时新增 ADR，并在索引和新旧 ADR 中写明 supersedes/superseded by。
- Proposed ADR 可以补充证据和待决项，但模型不能自行改成 Accepted。
- ADR 状态必须和 `docs/adr/README.md` 一致。
- “已实现”“技术验收完成”“已上线”“已治理签署”是不同状态，必须分别给出证据。

## 3. 证据规则

- 命令、路径、类名、环境变量和 CI job 必须从当前工作区核对。
- 本地测试结果只能写成“本地验证”；GitHub Actions、镜像扫描、签名和生产演练必须引用真实远端结果。
- 目标数据库角色、未来模块或规划中的 RLS policy 必须标记为目标态，不能描述为当前事实。
- 未完成项要写清原因、前置条件、Owner/Reviewer 或验收证据，不能只写“后续优化”。
- 不把 `test-results*.xml`、coverage 或临时构建目录当作架构事实源。

## 4. 修改检查

- 检查相对链接、标题层级、表格列数、代码块命令和术语一致性。
- 架构图必须与文字依赖方向一致；简单关系优先使用表格或文字，不增加装饰性图。
- 更新架构状态时同步检查 ADR 索引、实施基线、模块指南、README 文档入口和相关 CI。
- 文档变更不能替代实现与测试；如果文档声称行为已经完成，必须先找到代码、迁移和测试证据。
