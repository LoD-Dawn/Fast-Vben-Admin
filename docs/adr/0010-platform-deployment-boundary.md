# ADR-0010：Platform 交付边界与内部限界上下文

- 状态：Proposed
- 日期：2026-07-20
- 关联文档：[模块化架构实施基线](../modular-architecture-implementation.md)
- 细化关系：细化 ADR-0003 和 ADR-0009 中 Platform 的装配边界

## 背景

现有 Platform 同时包含身份、租户、组织、权限、文件、短信、邮件和日志。直接把 `kernel`、`system`、`infra` 都提升为 Edition 模块，会立即增加版本、迁移、授权、菜单和兼容矩阵，但当前没有独立销售、独立升级或独立部署这些能力的产品要求。

## 决策

v1 的 Edition 只包含两类交付模块：

- 唯一必选模块 `platform`。
- `items`、`ioa`、`erp` 等可选业务模块。

`kernel`、`system`、`infra` 是 Platform 内部限界上下文，不是独立 Edition 模块：

```text
platform
  kernel   认证、用户、租户、RBAC、菜单、模块运行时
  system   部门、岗位、字典、参数、公告
  infra    文件、存储、短信、邮件、日志、Outbox Transport
```

约束：

- `platform` 始终包含在所有 Edition 中，不能被普通模块管理接口停用。
- Platform 内部包可以渐进迁移，v1 继续共用平台版本和 `public` Schema 迁移链。
- 业务模块只能调用 `platform.public_api` 和 `platform.web_api`，不能导入内部上下文。
- `kernel` 不能导入 `system`、`infra` 的业务实现；组合根可以装配三者。
- 文件、消息等能力通过 Platform capability 暴露，调用方不感知内部实现位置。
- 只有出现独立授权、独立发布、独立扩容或合规隔离需求时，才通过新 ADR 将某个内部上下文提升为 Edition 模块。

v1 Edition：

| Edition | 模块 |
| --- | --- |
| `base` | `platform` |
| `items` | `platform, items` |
| `suite` | `platform` 加所有已交付业务模块 |

## 结果

Platform 内部仍能按所有权拆分代码和模型，但不会过早扩大 Edition 组合数量。业务模块获得稳定平台接口，后续提升某个内部上下文时不要求修改业务核心。

## 验收标准

- Edition 文件不出现 `kernel`、`system`、`infra`。
- Platform 内部导入方向由架构测试检查。
- Items 不导入任何 Platform 内部实现。
- Base 包含完整 Platform 管理能力，但不装配任何业务模块。
