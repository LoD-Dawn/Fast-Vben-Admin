# ADR-0005：多模块数据库迁移编排

- 状态：Proposed
- 实施细化：[ADR-0014](./0014-deployment-readiness-and-runtime-degradation.md) 区分部署失败和运行期降级
- 日期：2026-07-19
- 关联文档：[模块化产品架构规划](../modular-product-architecture.md)
- 修订关系：接受后部分修订 [ADR-0002](./0002-multi-tenancy-shared-schema.md) 中“shared schema”的范围

## 背景

当前项目只有一套 Alembic 环境、全局 SQLModel metadata 和单一 `alembic upgrade head`。当 IOA、ERP 可以选择性构建并由不同开发节奏维护时，继续使用同一条 revision 链会导致多 head、合并迁移冲突和不同 edition 的迁移历史不一致。

## 决策

平台与每个业务模块使用独立 Alembic 迁移环境和独立版本表，由统一迁移编排器执行。

ADR-0002 的 shared schema 继续表示“同一模块内的所有租户共享 Schema，并使用 `tenant_id` 隔离”，不再表示整套应用的所有模块必须位于同一个 PostgreSQL Schema。模块 Schema 是代码和数据所有权边界，不是租户隔离边界。

为降低现有系统改造风险：

- 现有平台表暂时保留在当前 `public` Schema 和现有 Alembic 版本表中。
- 新 IOA 表进入 `ioa` Schema。
- 新 ERP 表进入 `erp` Schema。
- 是否将现有平台表迁入 `platform` Schema 另行决策，不作为模块化前置条件。

版本表使用明确名称并保存在 `public` Schema：

```text
alembic_version
alembic_version_ioa
alembic_version_erp
```

每个模块的 Alembic 环境只加载和比较本模块拥有的 metadata，禁止自动生成其他模块表的删除或修改操作。实现必须满足：

- 新模块模型显式声明固定 Schema，不依赖可变 `search_path` 判断表归属。
- Alembic 启用 `include_schemas=True`。
- 使用 `include_name` 或 `include_object` 将 autogenerate 限制在模块拥有的 Schema 和表集合。
- 模块内外键使用 Schema-qualified 表名；继续禁止跨模块数据库外键。
- 版本表通过 `version_table` 和 `version_table_schema="public"` 显式配置。
- CI 检查 autogenerate 结果，ERP 迁移不得生成 IOA 或平台表的删除、重命名和修改操作。

当前 `SQLModel.metadata` 是全局对象。模块迁移可以从全局 metadata 构建只读的模块表视图或使用 Alembic 过滤器，但过滤逻辑必须集中在迁移基础设施中，不能由每个模块自行复制。

统一迁移编排器按以下步骤执行：

1. 获取 PostgreSQL advisory lock，防止多个部署实例同时迁移。
2. 读取 Build Manifest 并验证模块依赖拓扑。
3. 校验模块声明的最低平台 Schema revision 和依赖模块 Schema revision。
4. 先执行平台迁移。
5. 按拓扑顺序执行当前 edition 中业务模块的迁移。
6. 将目标版本、实际版本、开始时间、完成时间和错误记录到模块状态表。
7. 任一模块迁移失败时停止启动，应用不进入 readiness 状态。
8. 修复后允许幂等重试，不能把失败模块标记为 ready。

迁移原则：

- 一个迁移文件只能修改所属模块的数据结构。
- 跨模块数据转换通过显式升级任务完成，不写入其他模块 Alembic revision。
- 生产迁移采用 expand/contract，应用部署流程不自动 downgrade。
- 禁用或移除模块不自动删除 Schema 和业务数据。
- 物理删除模块数据必须是独立、显式、可审计的管理操作。
- 长时间数据回填与 DDL 分离，并提供进度和恢复能力。

## 结果

优点：

- IOA、ERP 可以独立维护迁移历史。
- 在已有 Base 数据库中增加模块时，只运行新增模块迁移。
- 一个模块迁移失败时状态可识别，不会产生“整体 head 已完成”的错误判断。

代价：

- 需要迁移编排器和多套 Alembic 配置。
- SQLModel metadata 必须按模块过滤，模型归属需要严格治理。
- 跨模块 Schema 变更不能依靠一次 autogenerate 完成。

## 验收标准

CI 必须覆盖：

- `base`、`ioa`、`erp`、`suite` 从空库迁移。
- 从上一发布版本升级到当前版本。
- 已有 Base 数据库新增 IOA 或 ERP。
- 禁用模块后升级其他模块，原模块数据保持不变。
- 人为制造某模块迁移失败，确认应用不进入 ready，修复后可以继续执行。
- 并发启动两个迁移实例时只有一个实际执行。
- 对每个模块运行 autogenerate 空变更检查，确认不会触碰其他模块拥有的表。
