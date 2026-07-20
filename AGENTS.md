# Fast Vben Admin Agent Development Standard

本文件是所有自动化编码模型、代码生成模型和人工协作者的仓库级开发规范。进入任何子目录工作时，还必须读取并遵守距离目标文件最近的 `AGENTS.md`。子目录规范只能补充本文件，不能放宽本文件中的架构、安全和验证要求。

- 规范版本：1.0
- 架构基线：`docs/modular-architecture-implementation.md`
- 维护方式：架构变更与相关 `AGENTS.md` 在同一变更中更新

## 1. 开始工作前

在修改代码前，按顺序完成：

1. 阅读本文件和目标目录下的 `AGENTS.md`。
2. 阅读与任务相关的事实源、ADR、现有实现和测试。
3. 执行 `git status --short`，识别并保留用户已有修改。
4. 用 `rg` 定位现有实现、调用方、测试和兼容入口。
5. 明确变更边界、数据所有者、迁移影响、Edition 影响和验证范围。

不要只依据需求描述、文件名或旧对话推断当前实现。代码、迁移、CI 和当前文档才是工作区事实。

## 2. 决策优先级

发生冲突时按以下顺序处理：

1. 当前任务的明确要求。
2. 已接受的 ADR。
3. [模块化架构实施基线](docs/modular-architecture-implementation.md)。
4. [模块开发指南](docs/module-guide.md)和目标目录规范。
5. 当前代码与测试反映的兼容约束。

不要直接改写已经 Accepted 的 ADR 历史结论。需要改变已接受决策时，新增 ADR 并声明替代关系。Proposed ADR 不能由模型自行改成 Accepted；必须有团队签署和文档要求的演练证据。

## 3. 固定架构

- 架构形态是“模块化单体 + 构建期 Edition 组合”。当前阶段不拆微服务、不引入运行时微前端、不维护产品分支。
- `platform` 是每个 Edition 必选的交付模块。`kernel`、`system`、`infra` 只是 Platform 内部限界上下文，不得加入 Edition YAML 或单独授权。
- `items` 是业务模块样板。新增 IOA、ERP 等模块必须复用同一种模块契约、迁移、公开 API、事件和前端装配方式。
- 新业务能力进入 `backend/app/modules/<module_code>` 和 `frontend/apps/web-antd/src/modules/<module_code>`，不得继续扩大中央业务模型、中央 Router 或全局业务页面。
- 业务模块只能依赖 Platform 稳定公开接口和其他模块的 `public_api`。禁止导入其他模块的 `domain`、`application`、`infrastructure`、`routes` 或 ORM 实体。
- 可选能力通过 capability 契约和组合根选择 Provider。禁止从可选模块实现建立静态依赖。

## 4. 唯一事实源

| 信息 | 人工维护的唯一事实源 | 禁止做法 |
| --- | --- | --- |
| Edition 模块集合 | `editions/<edition>.yaml` | 用环境变量或菜单临时增加模块 |
| 模块契约 | `ModuleDefinition` | 在多个组合根重复声明 Router、权限或事件 |
| 构建组合 | 生成的 `build-manifest.json` | 前后端相互覆盖 Manifest |
| 模块期望/实际状态 | `ModuleRegistry` 与迁移/健康检查 | 请求鉴权时同步或创建运行时记录 |
| 套餐权益/例外/租户偏好 | `TenantPlanModule` / `TenantModuleEntitlementOverride` / `TenantModule` | 通过菜单或表存在性推断模块可用 |
| 用户权限 | Permission、Role、Menu 关系 | 只依赖前端按钮隐藏 |
| 数据表所有权 | Platform migration metadata 或模块自己的 migration namespace | 多模块共同拥有同一张表 |

派生文件必须通过仓库命令生成，不得手工维护生成结果。

## 5. 多租户与安全红线

- 租户身份只能来自已验证 JWT、可信事件信封、受控 client-to-tenant resolver、Schedule 的平台枚举结果或显式受审计的平台入口。
- 不得直接信任 body、query、header 中的 `tenant_id`。公开回调必须先通过租户编码、客户端凭据或其他可信映射解析租户，再进入 UoW。
- Tenant-owned 数据必须在对应 TenantUnitOfWork 内访问。API、Worker、Schedule、CLI 使用相同隔离原则。
- `privileged=True` 仅用于已经完成平台级授权的受控跨租户操作。调用点必须可审计，并具有跨租户负向测试。
- ORM tenant 过滤不是 PostgreSQL RLS 的替代品；RLS 也不是可信租户解析的替代品。扩展 RLS 时必须同时更新模型集合、迁移、runtime 角色测试和调用路径。
- 不得假设所有带 `tenant_id` 的历史表已经启用 RLS。OAuth2/OIDC、租户全局目录和全局模块运行时表的前置设计见实施基线和 ADR-0013。
- 运行时进程使用无超级用户、无建库/建角色、无 `BYPASSRLS` 的 `app_runtime`。迁移管理员凭据不得注入 API 或 Worker。
- 禁止提交密钥、真实密码、访问令牌、个人数据或生产连接信息。

## 6. 模块、API 与事件

- 业务模块后端入口必须使用 `require_module_access("<module>", "<permission>")`，Platform 管理能力使用对应 `require_permission`。
- 前端权限只用于交互体验；真正的安全边界必须在后端。
- 跨模块公开接口只暴露 DTO、不可变值对象、稳定错误码和版本化契约，不暴露 ORM、Session、Request 或第三方 SDK 对象。
- 改变其他模块业务状态时使用事务 Outbox。事件 Schema 放在发布方 `public_api.events`，消费者按 event ID 幂等处理。
- 无消费者、可选消费者、重试、租约、死信和回执必须遵循现有 Outbox 状态机，不能新增旁路投递方式。
- 破坏性 HTTP、DTO、事件或公开 API 变更必须提供版本策略、兼容窗口和迁移说明。

## 7. 数据库与迁移

- 历史 Alembic revision 一经进入共享历史不得改写；新增 revision 接在正确 namespace 的当前 head 后。
- Platform 使用 Platform Alembic 链；业务模块使用自己的 schema、版本目录和版本表。
- 模型、约束、索引、外键、RLS policy、降级逻辑和授权必须在迁移中显式表达。
- 禁止用启动时 `create_all`、请求副作用或手工 SQL 替代迁移。
- 修改迁移体系后必须运行对应 migration tests、`alembic check` 和受影响 Edition 构建。

## 8. 生成代码与兼容入口

- 不手工编辑 OpenAPI 生成客户端、类型文件或 Build Manifest。修改源契约后重新生成。
- `app.models`、`app.core.db` 以及旧 Router/Infra 路径是兼容门面，不是新增生产依赖入口。
- 不删除兼容门面，除非任务明确包含迁移期结束、所有消费者审计和破坏性变更方案。
- 生成器输出只是起始代码。合并前必须迁入目标模块结构并补齐权限、租户、迁移和测试。

## 9. 修改原则

- 优先遵循现有模式；只在减少真实复杂度或匹配既有边界时增加抽象。
- 变更保持最小且完整：修复根因、所有调用方、测试、迁移和文档，不做无关重构。
- 不回滚、覆盖或格式化与任务无关的用户修改。
- 禁止为了让测试通过而放宽鉴权、租户隔离、RLS、错误处理或契约校验。
- 对暂不能安全完成的范围，明确前置条件和失败关闭行为，不用占位实现伪装完成。

## 10. 验证矩阵

按变更风险选择测试，不能用窄测试证明宽范围完成：

| 变更 | 最低验证 |
| --- | --- |
| Python 代码 | `cd backend && uv run ruff check app tests` + 受影响 pytest |
| 数据模型/迁移 | upgrade、对应 migration tests、`uv run alembic check` |
| Tenant/RLS | `app_runtime` 角色下的读写、bulk DML、无 scope、跨租户负向测试 |
| API/DTO | 路由测试；影响前端时重新生成 OpenAPI 客户端 |
| 模块契约/装配 | manifest、边界、迁移和 Edition tests |
| 前端 TypeScript/Vue | `pnpm frontend:typecheck` + 受影响构建 |
| Edition/Manifest | `pnpm build:edition -- --edition base`、`items`、`suite` |
| Compose/部署 | `docker compose config` + 对应健康/启动验证 |
| 架构文档/ADR | 路径、状态、命令和实现证据核对 |

共享数据库测试不得并行运行，避免 fixture 互相清理产生伪失败。测试报告、coverage、构建目录和 `artifacts/` 是派生产物，除非发布流程明确要求，不提交到源码。

## 11. 完成定义

只有同时满足以下条件才能宣称完成：

- 行为与任务一致，失败路径和权限边界明确。
- 架构依赖方向、事实源和模块所有权未被破坏。
- 数据迁移、兼容策略和回滚影响已处理。
- 测试覆盖与变更风险匹配，实际命令已成功完成。
- 文档描述当前事实，不把目标态、建议或本地结果写成已上线事实。
- 明确列出未执行的外部门禁，例如远端 CI、镜像扫描、签名、N-1 演练或团队签署。

“文件已创建”“局部测试通过”或“实现看起来合理”都不构成完成证据。

## 12. Git、依赖与交付

- 未经明确要求，不创建分支、不暂存、不提交、不推送、不创建 PR，也不修改远端状态。
- 禁止使用 `git reset --hard`、强制推送或其他会覆盖未提交工作的操作。不要回滚无法确认来源的修改。
- 新增运行时依赖前，先证明标准库和现有依赖不能合理解决问题；同步更新 lockfile、镜像和供应链检查。
- 不在功能任务中顺带升级框架、格式化全仓库或重写无关生成文件。
- 交付说明至少包含：行为变化、关键文件、实际执行的验证、未执行的验证、兼容/迁移影响和已知剩余风险。
