# ADR-0013：TenantUnitOfWork 与 PostgreSQL RLS

- 状态：Proposed
- 日期：2026-07-20
- 关联文档：[模块化架构实施基线](../modular-architecture-implementation.md)
- 细化关系：细化 ADR-0002 的共享 Schema 隔离实现

## 背景

仅依赖 Router 手工增加 `tenant_id` 条件，无法覆盖遗漏查询、Worker、定时任务、CLI、bulk DML 和 raw SQL。`ContextVar` 可以传播上下文，但不能替代明确的数据库访问边界。

## 决策

### 1. Unit of Work

租户业务访问必须通过显式 `TenantUnitOfWork(tenant_id)`：

- API 从已验证的 TenantContext 创建 UoW。
- Event Consumer 从可信事件信封创建 UoW。
- Schedule 先由平台任务列出 tenant_id，再逐租户创建 UoW。
- CLI 必须显式传入 tenant_id 或使用受审计的 PlatformUnitOfWork。
- 缺少 tenant_id 时失败关闭。

`ContextVar` 只用于在调用链中传播当前 UoW，不是租户身份的事实源。

### 2. ORM 防护

- `TenantOwned` 模型强制包含不可变 `tenant_id`。
- Session 对查询自动应用 `with_loader_criteria`。
- `before_flush` 校验新增、更新和关联对象的 tenant_id。
- Tenant UoW 禁止 ORM bulk update/delete 和未包装 raw SQL。
- 跨租户平台操作使用独立 `PlatformUnitOfWork`，业务模块不能导入其工厂。

### 3. 数据库角色

当前技术验收已实际启用 `app_runtime`。它运行 API、Worker 与 Schedule，且经 PostgreSQL 角色属性和 runtime 回归验证为非超级用户、不能建库/建角色、无 `BYPASSRLS`。迁移和授权目前由部署阶段的管理员凭据执行，该凭据不注入运行时进程。

以下是待治理批准的目标角色模型，不能视为现状：

```text
app_runtime        租户 API、Worker，无 BYPASSRLS
app_platform       受审计平台跨租户操作，独立连接池，无 BYPASSRLS
app_migrator       DDL 和迁移，不提供给应用请求
app_readonly       受控运维查询
```

启用该目标模型前，`app_migrator` 必须拥有 Schema 和表，`app_runtime`、`app_platform` 都不能成为表 Owner。业务模块只接收 `app_runtime` Session，各角色使用独立凭据；`app_platform` 必须有独立连接池、受审计入口与 N-1 演练证据。

### 4. RLS

Items 和所有新业务模块表必须启用并强制 RLS：

```sql
ALTER TABLE items.item ENABLE ROW LEVEL SECURITY;
ALTER TABLE items.item FORCE ROW LEVEL SECURITY;
```

`app_runtime` 每个事务通过参数化 `set_config('app.tenant_id', tenant_id, true)` 设置事务级租户。策略在设置缺失或非法时返回无行/拒绝写入。连接归还池前事务必须结束，不使用跨事务 session-level `SET`。启用 `app_platform` 后，它使用只授予该角色的显式跨租户 policy，且不授予 `BYPASSRLS`。

现有 Platform 表按独立迁移计划逐步接入；在迁移完成前继续保留显式 tenant 条件和跨租户负向测试。

以下表组必须先建立可信 tenant 来源，不能仅增加 `tenant_id = current_setting(...)` policy：

| 表组 | 可信来源或前置拆分 |
| --- | --- |
| OAuth2 client/code/token | 受限的 client-to-tenant resolver；协议交换与 resolver 在同一事务 |
| Enterprise OIDC state/identity/ticket | 明确全局身份边界；仅 tenant 投影使用 UoW |
| TenantMembership/TenantProfile | 登录前成员和生命周期受控目录，或受审计平台查询入口 |
| ModuleStateAudit、Outbox、EventDelivery、Inbox | 全局控制面与 tenant event stream 分离；Worker claim 后逐事件 UoW |
| CapabilityBinding | tenant-aware repository/public API，不接受裸 Session |

## 结果

租户身份从请求参数提升为数据库访问边界，并覆盖 API、Worker、Schedule 和 CLI。Platform 跨租户能力仍可实现，但使用不同入口、连接池和审计策略。

## 验收标准

- 删除 Repository 中显式 tenant where 后仍不能读取其他租户数据。
- 未设置 tenant_id 的 runtime 事务不能读取或写入 TenantOwned 表。
- Worker 和 Schedule 的隔离测试与 API 使用相同测试集。
- bulk DML 和 raw SQL 绕过尝试被拒绝。
- 启用 `app_platform` 后，其每次跨租户写操作产生操作审计；在此之前，HTTP 平台路径必须维持操作审计，CLI 不得宣称同等保证。
