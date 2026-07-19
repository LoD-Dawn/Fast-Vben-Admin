# ADR-0003：Edition 与模块状态的唯一事实源

- 状态：Proposed
- 日期：2026-07-19
- 关联文档：[模块化产品架构规划](../modular-product-architecture.md)

## 背景

模块化方案涉及 edition 文件、环境变量、后端注册表、前端注册表和数据库模块状态。如果这些位置都能独立决定启用哪些模块，前后端和数据库会产生状态漂移，例如后端暴露 ERP API，但前端没有 ERP 页面，或者数据库声称模块已安装而镜像中并不存在该模块代码。

## 决策

`editions/<edition>.yaml` 是产品构建时模块集合的唯一人工维护事实源。

生产构建只接受 `APP_EDITION` 指定 edition，不再通过 `ENABLED_MODULES` 任意拼接模块。`ENABLED_MODULES` 如保留，只允许本地开发使用，并必须经过同一套依赖校验和 Manifest 生成流程。

构建工具读取 edition 及各模块声明，解析依赖后生成不可变的 `build-manifest.json`：

```json
{
  "edition": "suite",
  "platform_version": "1.0.0",
  "modules": [
    { "code": "platform", "version": "1.0.0" },
    { "code": "ioa", "version": "1.0.0" },
    { "code": "erp", "version": "1.0.0" }
  ],
  "manifest_digest": "sha256:..."
}
```

同一个 Manifest 生成以下产物：

- 后端静态模块注册表。
- 前端模块注册表和组件映射。
- 镜像标签及构建元数据。
- CI 的发行版测试矩阵输入。

数据库 `ModuleRegistry` 不决定镜像中是否包含模块代码，只保存模块运行期的期望状态和观测状态：

```text
desired_state: enabled / disabled / uninstall_pending
observed_state: bundled / migrating / ready / degraded
```

- `desired_state` 只能由平台模块管理接口修改，表达管理员期望模块启用、停用或进入卸载流程。
- `observed_state` 只能由构建校验、迁移编排器和健康检查更新，表达系统实际状态。
- 模块实际可用要求 `desired_state=enabled` 且 `observed_state=ready`。
- Build Manifest 是“代码是否存在”的唯一事实源，数据库不能把未打包模块变成已安装模块。

应用启动时执行一致性校验：

1. Manifest 中的模块依赖必须完整且无环。
2. 后端注册模块必须与 Manifest 完全一致。
3. 数据库中不能存在 `desired_state=enabled` 但代码不存在的模块。
4. 期望启用模块的迁移版本必须达到 Manifest 要求，并进入 `observed_state=ready`。
5. 前端启动时比较自身 Manifest digest 与后端公开的 digest。

任何关键校验失败都应 fail closed：后端不进入就绪状态，前端显示版本不一致错误，不继续加载业务菜单。

## 结果

优点：

- 可以重现任意发行版构建。
- 消除前端、后端和数据库各自维护模块集合造成的漂移。
- 区分管理员期望与系统实际状态，迁移失败不会被误判为模块已经启用。
- 为部署检查、故障定位和供应链审计提供统一依据。

代价：

- 需要新增 Manifest 生成和校验工具。
- edition 变化必须重新构建前后端产物，第一阶段不支持运行时安装前端模块。

## 验收标准

- 修改 edition 后可以一次生成前后端注册表和 Manifest。
- 人为删除一个模块注册项时构建或启动失败。
- 前后端部署了不同 Manifest 时，用户不能进入不一致的业务界面。
- `/api/v1/platform/modules/manifest` 可以返回不含敏感信息的版本和 digest。
- 将 `desired_state` 改为 `enabled` 不能直接覆盖迁移失败产生的 `observed_state=degraded`。
