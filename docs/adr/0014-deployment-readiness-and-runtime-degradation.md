# ADR-0014：部署门禁、Readiness 与运行期降级

- 状态：Proposed
- 日期：2026-07-20
- 关联文档：[模块化架构实施基线](../modular-architecture-implementation.md)
- 细化关系：消除 ADR-0005 与 ADR-0006 在迁移失败和运行期降级上的歧义

## 背景

部署期迁移失败与运行中单个业务模块依赖故障是两种不同场景。前者不能让不完整的新版本接收流量；后者不应必然让身份、租户和其他模块同时下线。

## 决策

### 1. 部署期

- 迁移由独立一次性 prestart Job 执行，不由每个 API 实例并发执行。
- 当前 Manifest 中任一模块迁移失败，新版本部署失败；迁移不因 desired_state=disabled 而跳过。
- 滚动部署期间旧版本继续服务；迁移必须满足 N/N-1 应用兼容窗口。
- 修复采用幂等重试或前向迁移，不自动 downgrade。

### 2. 启动期

API 实例启动时只验证，不修改运行状态：

- Manifest、静态注册表和代码一致。
- 数据库 revision 达到 Manifest 要求。
- Platform 处于 ready 且关键依赖可用。
- 业务模块处于 ready 或可隔离的 degraded；degraded 模块不会阻止实例为 Platform 和其他模块提供服务。

Manifest、revision 或 Platform 验证失败时实例不进入 readiness。业务模块 degraded 时实例可以 ready，但该模块访问依赖固定返回 503。发布控制器仍要求新版本所有期望启用模块在 rollout 前 ready，因此该规则不会允许迁移失败的新版本上线。

### 3. 运行期

- `platform` 是唯一 critical 模块。Platform 或数据库故障使整个实例退出 readiness。
- 业务模块默认 isolated。业务模块健康检查失败时进入 degraded，其 API 返回 `MODULE_UNAVAILABLE`，Worker 和 Schedule 暂停，但实例继续为 Platform 和其他模块服务。
- 依赖 degraded 模块的必选消费者同时 degraded；只依赖可选 capability 的消费者按声明执行降级或关闭功能。
- 恢复检查通过后，系统把业务模块恢复为 ready，并记录状态事件和审计。

### 4. 健康端点

- Liveness 只判断进程是否存活。
- Readiness 判断 Platform 和共享基础依赖能否服务。
- Module health 返回每个业务模块状态，不把业务模块故障伪装为健康。

v1 readiness 关键依赖固定为 PostgreSQL、Manifest/注册表一致性和 Platform migration revision。Redis、对象存储、SMTP、短信渠道、Sentry 及业务外部 Provider 默认按功能降级；新增依赖必须在模块 ConfigSpec 中显式分类。

## 结果

不完整的新版本无法接流量，运行中单个业务模块故障又不会扩大为整个平台不可用。

## 验收标准

- 人为制造 Items 迁移失败，新部署实例始终不 ready，旧版本继续服务。
- 运行中将 Items 置为 degraded，Items 返回 503，Platform API 保持可用。
- Items degraded 时重启现有版本 API，Platform 仍可进入 readiness，Items 继续保持 503。
- Platform 数据库不可用时 readiness 失败。
- 模块恢复后无需重启 API 实例即可恢复业务访问。
