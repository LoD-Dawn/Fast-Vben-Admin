# ADR-0011：Edition 制品策略与 Build Manifest v2

- 状态：Proposed
- 日期：2026-07-20
- 关联文档：[模块化架构实施基线](../modular-architecture-implementation.md)
- 细化关系：细化 ADR-0003 和 ADR-0008 的制品生成规则

## 背景

当前 Manifest 只包含模块版本，无法验证数据库 migration head 和 OpenAPI 契约。另一方面，要求 Base 镜像物理删除其他模块源码会迫使项目过早拆成多个 Python distribution，但当前 Edition 的产品目标是功能组合，不是源码授权隔离。

## 决策

### 1. 后端制品

v1 后端镜像允许包含仓库中的全部模块源码。安全与可用边界由构建期生成的静态注册表保证：未启用模块不得注册 Router、Worker、Schedule、事件消费者和迁移。

源码物理隔离不作为 v1 验收项。未来只有出现私有源码交付或独立依赖发布要求时，才把业务模块拆为独立 wheel。

### 2. 前端制品

前端生产 dist 只能包含当前 Edition 的模块入口。构建期生成静态模块注册表，Vite 仅从该注册表建立页面和 API 引用。

模块级生成客户端提交到仓库，CI 重新生成并执行 drift check。组合 OpenAPI 只用于文档和兼容性检查，不生成另一套共享客户端。

### 3. Manifest v2

Manifest 是确定性 JSON，规范字段为：

```json
{
  "schema_version": 2,
  "edition": "items",
  "source_revision": "git-commit-sha",
  "platform_contract_version": 1,
  "modules": [
    {
      "code": "platform",
      "version": "1.0.0",
      "migration_namespace": "platform",
      "migration_heads": ["revision-id"],
      "openapi_sha256": "sha256:..."
    }
  ],
  "manifest_digest": "sha256:..."
}
```

规则：

- `modules` 按依赖拓扑和模块编码稳定排序。
- 生产制品只允许从 CI 的干净、可追溯 Git checkout 构建；dirty worktree 只能生成本地开发产物，不能发布。
- 摘要不包含构建时间、镜像地址等非确定性字段。
- 构建时间、镜像 digest、SBOM 地址和签名放入独立 `artifact-metadata.json`。
- 生产后端必须从只读文件加载 Manifest，禁止运行时根据默认 Edition 重建。
- 前端内嵌相同 Manifest；首次加载比较后端公开摘要，不一致时进入版本错误页。
- 镜像使用 OCI label 记录 edition、source revision 和 manifest digest。

### 4. 统一构建

唯一构建入口按顺序执行 Manifest、注册表、契约、前端、镜像和冒烟测试。前后端不能分别选择 Edition。

## 结果

v1 避免不必要的 Python 包拆分，同时保证未启用代码没有运行入口。Manifest 可以真正参与迁移、契约和部署一致性校验。

## 验收标准

- 相同提交和 Edition 两次生成的 canonical Manifest 完全一致。
- 修改 migration head 或 OpenAPI 会改变 Manifest digest。
- Base 后端不暴露 Items 路由、任务和迁移；Base 前端 dist 不含 Items 入口。
- 前后端 Manifest 不一致时不能进入业务界面。
- 模块客户端重新生成后仓库无差异。
