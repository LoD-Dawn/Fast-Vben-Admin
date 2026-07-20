# ADR-0012：Outbox Delivery 与 Inbox 状态机

- 状态：Proposed
- 日期：2026-07-20
- 关联文档：[模块化架构实施基线](../modular-architecture-implementation.md)
- 细化关系：细化 ADR-0006 的可靠事件语义

## 背景

单个 Outbox 状态无法同时表达事件已经创建、已交给外部 Broker、本地消费者已处理和部分消费者失败。把这些状态都称为 `PUBLISHED` 会产生错误重试或静默丢事件。

## 决策

### 1. 数据模型

```text
OutboxEvent
  id, event_type, event_version, aggregate_id, aggregate_sequence
  tenant_id, payload, occurred_at
  status: pending / complete / dead_letter

EventDelivery
  event_id, target_name, target_type, required
  status: pending / processing / delivered / dead_letter
  attempts, available_at, locked_by, locked_until, last_error

InboxReceipt
  consumer_name, event_id, processed_at
  UNIQUE (consumer_name, event_id)
```

`target_type` 首期支持：

- `local_consumer`：模块化单体内的消费者。
- `external_broker`：外部消息中间件确认接收。

### 2. 状态语义

- 业务数据和 `OutboxEvent`、初始 `EventDelivery` 在同一事务提交。
- Worker 在短事务中领取 Delivery 并写入带过期时间的租约，然后关闭领取事务。
- 本地消费者在消费者模块事务中提交业务副作用和 `InboxReceipt`。
- 消费成功后单独确认 Delivery；若在两者之间崩溃，重试读取 InboxReceipt 后直接确认，不重复业务副作用。
- 外部 Broker Delivery 只有在 Broker ACK 后标记 `delivered`。
- 所有 required Delivery 成功后，OutboxEvent 进入 `complete`。
- required Delivery 进入死信时，OutboxEvent 进入 `dead_letter`；optional Delivery 失败只告警，不阻塞完成。
- 没有 Delivery target 且事件契约未显式声明 `allow_zero_subscribers` 时属于构建配置错误。
- `allow_zero_subscribers` 只适用于生命周期通知等当前 Edition 可以无人消费的事件；业务上必须改变下游状态的事件禁止使用。

不再使用 `PUBLISHED` 表示消费者完成。

### 3. 重试与顺序

- 租约超时后其他 Worker 可以重新领取。
- 重试使用带抖动的指数退避，最大次数由 target policy 声明。
- 错误只保存稳定错误码和截断摘要，敏感 payload 不写入日志。
- 要求同聚合顺序的事件必须携带单调 `aggregate_sequence`；前序 required Delivery 未完成时不领取后序 Delivery。
- 禁用消费者模块时，该模块的 Delivery 保持 pending，不增加失败次数。

### 4. 事务边界

消费者不能依赖发布方 ORM。未来拆服务后，InboxReceipt 跟随消费者数据库，Delivery 仍只表示 Transport 已经完成交付。

## 结果

事件交付和消费状态不再混淆，Worker 可以在崩溃、重复投递和多消费者部分失败时安全恢复。

## 验收标准

- 零 target 且未允许零订阅者的 required 事件在构建时失败。
- 消费者提交后、Delivery 确认前崩溃不会重复业务副作用。
- 租约超时事件可被其他 Worker 领取。
- required 与 optional target 的完成语义测试通过。
- 同 aggregate 的 required 事件不会乱序处理。
