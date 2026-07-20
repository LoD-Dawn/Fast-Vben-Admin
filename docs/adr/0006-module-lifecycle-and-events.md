# ADR-0006：模块生命周期与跨模块事件可靠性

- 状态：Proposed
- 实施细化：[ADR-0012](./0012-outbox-delivery-inbox-state-machine.md) 和 [ADR-0014](./0014-deployment-readiness-and-runtime-degradation.md)
- 日期：2026-07-19
- 关联文档：[模块化产品架构规划](../modular-product-architecture.md)

## 背景

模块不只有启用和禁用两种状态。它还会经历构建、迁移、故障、升级和待卸载。与此同时，ERP 与 IOA 的审批等协作会产生跨模块状态变化，不能依靠进程内临时调用保证可靠性。

## 决策

模块生命周期拆分为管理员期望状态和系统观测状态：

```text
desired_state: enabled / disabled / uninstall_pending
observed_state: bundled → migrating → ready
                                  ↘ degraded

effective_state = enabled
  only when desired_state=enabled and observed_state=ready
```

状态语义：

| 类型 | 状态 | 语义 |
| --- | --- | --- |
| 期望 | `enabled` | 管理员期望模块提供服务 |
| 期望 | `disabled` | 管理员要求停止新业务，数据保留 |
| 期望 | `uninstall_pending` | 管理员已申请卸载，等待归档和人工确认 |
| 观测 | `bundled` | 代码存在于当前构建产物中，尚未确认数据库状态 |
| 观测 | `migrating` | 正在执行迁移，不接收业务请求 |
| 观测 | `ready` | 迁移、依赖和健康检查通过 |
| 观测 | `degraded` | 迁移、依赖或健康检查异常，只允许管理和恢复操作 |

`desired_state` 由平台模块管理接口修改，`observed_state` 由构建校验、迁移编排器和健康检查修改。任何调用方都不能通过写入期望状态伪造观测状态。

全局禁用模块时：

- 立即拒绝新的业务写请求。
- Worker 不再领取该模块的新任务。
- 定时任务不再创建新业务记录。
- 未处理事件保留，不标记为成功。
- 历史数据默认保留，只能通过受审计的维护接口导出或处理。

模块物理卸载默认不删除数据。Schema 删除必须经过独立审批、备份确认和显式管理命令。

模块契约除路由、菜单和健康检查外，还必须声明：

- metadata 和迁移配置。
- 配置 Schema 与敏感配置要求。
- 事件发布和订阅声明。
- Worker、定时任务及其停止钩子。
- 启动、就绪、禁用和恢复钩子。
- 依赖的必选及可选能力。

### 能力提供者绑定

业务实例创建时记录实际能力提供者和版本。例如 ERP 审批单记录：

```text
provider_code = ioa
provider_version = 1
external_instance_id = ...
```

后续安装、禁用或替换 IOA 不得让进行中的实例自动切换到简单审批。旧实例必须继续由原提供者完成，或者进入明确的人工迁移流程。

### 事件可靠性

凡是会改变其他模块业务状态的跨模块事件，都必须使用事务 Outbox，而不是把 Outbox 作为可选增强：

1. 业务状态和 Outbox 记录在同一数据库事务中提交。
2. 独立 Worker 投递事件。
3. 消费者使用 `event_id` 记录幂等处理结果。
4. 失败执行指数退避，超过阈值进入死信并触发告警。
5. 事件包含 `event_id`、`event_type`、`event_version`、`tenant_id`、`aggregate_id`、`occurred_at` 和追踪标识。
6. 同一聚合需要顺序时使用 `aggregate_id` 作为排序或分区键。
7. 事件字段只能向后兼容扩展；破坏性变更发布新事件版本。

进程内同步事件只允许用于不影响业务正确性的扩展，例如指标采集。同步跨模块查询必须设置超时；未来拆分服务后还需要熔断和明确的降级行为。

## 结果

优点：

- 模块禁用、升级和故障时行为可预测。
- 审批等长事务不会因能力提供者切换而失去归属。
- 跨模块状态变更具备可重试、可审计和可观测能力。

代价：

- 第一阶段需要新增 Outbox 表、投递 Worker、幂等记录和死信处理。
- 模块开发者必须维护事件契约和生命周期钩子。
- 卸载流程比删除菜单和路由更严格。

## 验收标准

- `desired_state` 和 `observed_state` 的变化分别保留操作审计与系统事件记录。
- 把期望状态改为 `enabled` 时，如果观测状态不是 `ready`，模块仍不能接收业务请求。
- 禁用模块后不会产生新的业务任务，但原数据仍可按维护策略处理。
- Outbox 投递进程被中断后，恢复时不会丢失或重复执行业务效果。
- IOA 禁用时，已绑定 IOA 的进行中审批不会自动切换实现。
- 死信事件可以查询、告警、修复并重新投递。
