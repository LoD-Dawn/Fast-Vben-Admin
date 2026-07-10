# 新增业务模块指南

以 Items 为范例，一个完整模块应包含：

- SQLModel 数据模型。
- Alembic 迁移。
- CRUD/API 路由。
- 权限码和初始化菜单。
- 前端 API 封装。
- 前端列表、查询、新增、编辑、删除页面。
- 测试和文档。

## 后端

1. 在 `models.py` 定义 `XxxBase`、`XxxCreate`、`XxxUpdate`、`Xxx`、`XxxPublic`、`XxxsPublic`。
2. 新建 `api/routes/xxx.py`。
3. 在 `api/main.py` include router。
4. 在 `core/db.py` seed 菜单和按钮权限。
5. 增加测试，至少覆盖 CRUD、权限、分页和关键校验。

## 前端

1. 在 `src/api/core/xxx.ts` 封装接口。
2. 在 `src/views/xxx/index.vue` 实现页面。
3. 如果使用前端静态路由，在 `src/router/routes/modules` 增加路由；后端菜单模式下，确保后端菜单 `component` 指向页面。
4. 给新增、编辑、删除、导入导出等按钮加 `v-access:code` 或表格 `auth`。
5. 从仓库根目录运行 `pnpm generate:api`、`pnpm frontend:typecheck`、`pnpm frontend:build`。

## 发布前检查

新增模块进入发布前，至少确认：

- 后端路由使用 `require_permission("<domain>:<resource>:<action>")`。
- `backend/app/core/db.py` 初始化了对应菜单和按钮权限。
- 前端页面没有绕过权限展示危险操作入口。
- `pnpm generate:api` 生成的类型已提交。
- `uv run pytest` 和 `pnpm frontend:build` 通过。
