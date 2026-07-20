# Backend Agent Standard

本文件适用于 `backend/` 下的所有修改，并补充仓库根目录 [AGENTS.md](../AGENTS.md)。

## 1. 技术与代码风格

- 使用 Python 3.14、FastAPI、SQLModel、SQLAlchemy、Alembic 和 Pydantic v2 的现有模式。
- 时间统一使用 `app.core.clock.get_datetime_utc()` 和带时区字段。
- 使用结构化查询 API；除迁移、RLS setting 和明确封装的基础设施外，不新增裸 SQL。
- Router 负责 HTTP 契约、依赖注入和事务边界；可复用业务规则进入 application/service 或当前所属上下文服务。
- 错误使用稳定 HTTP 状态与项目异常映射，不能向客户端泄露密钥、SQL、堆栈或内部对象。
- 新生产代码直接导入物理所有者模块。不要从 `app.models` 或 `app.core.db` 引入已迁移模型、数据库连接或 bootstrap 服务。

## 2. Platform 边界

- `app/platform/core` 不导入 Infra、Router 或业务模块。
- `app/platform/infra` 可以依赖 Platform core 契约，但不能拥有 RBAC、租户或业务单据状态。
- `app/platform/bootstrap.py` 是组合根，只编排；配置、导航和 RBAC 播种分别保存在现有子 bootstrap。
- Platform 表必须在 `app/platform/migration_metadata.py` 中有且仅有一个 owner。
- 旧 `app.api.routes.*`、`app.audit`、`app.mail`、`app.storage` 等兼容路径只做转发，不增加新逻辑。

## 3. 业务模块边界

新增或扩展模块遵循：

```text
app/modules/<module>/
  module.py
  public_api/
  domain/
  application/
  infrastructure/
  routes/
  migrations/
```

- `module.py` 是模块声明入口，定义 Router、权限、菜单、迁移、事件和生命周期组件。
- `public_api` 不得反向导入 `domain`、`application`、`infrastructure`、`routes` 或 FastAPI。
- Repository 和 ORM 由模块 infrastructure 拥有；Platform 和其他模块不得直接查询这些表。
- 必选模块依赖必须同时存在于 `ModuleDefinition.dependencies` 和静态 import 中；可选依赖只能走 capability。

## 4. 鉴权与数据权限

- 业务模块路由使用 `require_module_access`；Platform 路由使用精确的 permission dependency。
- 列表、详情、更新、删除和导出必须使用一致的数据权限范围，不能只保护列表接口。
- 超级管理员绕过只能发生在现有授权层，不能散落到 Repository 或查询条件。
- 用户、租户、角色、菜单等 Platform 主数据通过 Platform 公开端口访问，业务模块不能导入 Platform ORM。

## 5. Tenant UoW 与 RLS

- API 在认证依赖解析可信 tenant 后激活 Platform/模块 UoW；Worker 从事件信封进入 UoW；Schedule 逐租户执行。
- 写入 tenant-owned 实体时，调用方提供的 tenant ID 不能覆盖 UoW tenant；跨租户写入必须在 flush 前失败。
- tenant ID 不可变。禁止通过 update DTO、bulk update 或 ORM merge 改写归属。
- Platform 新增 RLS 表时同步更新 `TENANT_SCOPED_MODELS`、Alembic policy、授权脚本与 runtime 回归。
- UoW 退出必须恢复父 scope；最外层退出必须清空 PostgreSQL `app.tenant_id`，防止连接或 Worker 事务残留。
- OAuth2/OIDC、TenantMembership/Profile、全局 Outbox 和 module audit 等特殊表不得直接套用普通 policy；先落实实施基线中的可信 resolver/控制面拆分。

## 6. 数据库迁移

- Platform revision 放入 `app/alembic/versions`，接 Platform 当前 head。
- 模块 revision 放入模块自己的 `migrations/versions`，使用独立 schema 和版本表。
- 不修改历史 revision，不硬编码可能变化的 head；使用 Alembic ScriptDirectory 获取实际 head。
- upgrade 和 downgrade 必须处理 policy、constraint、index、schema 与数据兼容。
- 运行时角色需要新表权限时，更新幂等授权流程并验证角色属性。

## 7. Outbox 与公开契约

- 业务状态和 OutboxEvent 在同一事务提交。
- 发布事件使用发布模块 `public_api.events` 中的版本化 Schema，不传 ORM 或自由格式内部对象。
- 消费者副作用和 InboxReceipt 在同一嵌套事务，失败必须完整回滚。
- 不跳过 delivery、lease、retry、dead-letter 和 required/optional consumer 规则。
- 公共命令应有幂等键；公共查询返回 DTO，不返回 Session 或 ORM。

## 8. 后端验证

常用命令：

```powershell
cd backend
uv run ruff check app tests
uv run pytest <受影响测试> -q
uv run alembic check
```

完整数据库测试使用管理员连接；RLS 验证必须额外使用 `app_runtime`：

```powershell
$env:POSTGRES_SERVER = 'localhost'
$env:POSTGRES_USER = 'app_runtime'
$env:POSTGRES_PASSWORD = '<local-runtime-password>'
uv run pytest tests/platform/test_platform_tenant_scope.py <受影响路由测试> -q
```

不要在文档或规范中固化本地密码。最终交付说明必须区分管理员回归和 runtime 角色回归。
