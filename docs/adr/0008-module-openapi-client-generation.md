# ADR-0008：模块级 OpenAPI 与前端客户端生成

- 状态：Proposed
- 日期：2026-07-19
- 关联文档：[模块化产品架构规划](../modular-product-architecture.md)

## 背景

当前项目从完整 FastAPI 应用导出一份 OpenAPI，并把客户端生成到固定目录。不同 edition 注册的业务 Router 不同，如果继续共用一个生成目录，Base、IOA、ERP 和 Suite 会互相覆盖生成结果，也可能让未启用模块的类型和接口进入错误的前端产物。

## 决策

平台和每个业务模块分别拥有 OpenAPI 子契约及生成客户端，同时保留组合后的 OpenAPI 供当前 edition 的接口文档使用。

推荐目录：

```text
frontend/apps/web-antd/src/api/generated/platform/
frontend/apps/web-antd/src/modules/ioa/api/generated/
frontend/apps/web-antd/src/modules/erp/api/generated/
```

契约生成规则：

1. 平台契约只包含平台拥有的 Router 和 Schema。
2. 模块契约只包含本模块 Router 以及其公开请求和响应 Schema。
3. edition 构建根据 Build Manifest 生成所选模块客户端，不覆盖其他模块目录。
4. 组合应用继续暴露当前 edition 的 `/api/v1/openapi.json` 和 Swagger 文档。
5. 生成产物按模块提交或统一在 CI 生成，但仓库只能选择一种策略，不能部分模块提交、部分模块临时生成。

为避免组合 OpenAPI 冲突：

- API 路径必须包含模块前缀，例如 `/api/v1/erp/*`。
- `operation_id` 必须带模块命名空间并在组合契约中全局唯一。
- 公开 Schema 名称必须全局唯一，推荐使用 `ErpPurchaseOrderPublic` 等领域前缀。
- CI 对组合 OpenAPI 执行重复 operation ID、重复 Schema、悬空引用和客户端生成检查。

根命令扩展为 edition 感知的生成流程：

```text
pnpm generate:api --edition base
pnpm generate:api --edition ioa
pnpm generate:api --edition erp
pnpm generate:api --edition suite
```

模块开发时可以只生成单个契约，但发布前必须用相同 Build Manifest 完成组合契约验证。前端业务模块只能导入自己的生成客户端和平台公开客户端，不能导入其他可选模块客户端。

## 结果

优点：

- 不同 edition 不再争用同一个生成目录。
- 模块 API 依赖与代码边界一致。
- Base 构建不会因为 Suite 的生成结果意外引用 IOA、ERP 接口。

代价：

- 需要把当前单一 OpenAPI 生成脚本拆成平台、模块和组合三个层次。
- 公共 Schema 需要明确归属，不能通过随意跨模块导入复用。
- CI 构建矩阵的客户端生成时间会增加。

## 验收标准

- 连续生成 `base` 和 `suite` 不会删除或覆盖不相关模块的客户端目录。
- Base 前端生产产物不存在 IOA、ERP API 调用代码。
- 每个模块客户端都能仅从该模块子契约独立生成。
- 组合 OpenAPI 不存在重复 operation ID、Schema 名或悬空 `$ref`。
- 后端 API 变更但未更新对应模块客户端时 CI 失败。

