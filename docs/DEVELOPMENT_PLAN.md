# Fast Vben Admin v1.0 可落地实施计划

## 1. 文档信息

| 项目 | 内容 |
| --- | --- |
| 文档名称 | Fast Vben Admin v1.0 实施计划 |
| 关联文档 | [PRD](./PRD.md)、[TRD](./TRD.md)、[RBAC](./rbac.md)、[API 契约](./api-contract.md) |
| 参考项目 | `参考项目/LZ-litchi`、`参考项目/LZ-litchi-ui-admin-vben`、当前仓库实现 |
| 计划版本 | v0.3 |
| 更新日期 | 2026-07-09 |
| 目标版本 | v1.0.0 |
| 适用对象 | 后端、前端、测试、运维、项目维护者 |

## 2. 实施目标

本计划用于指导当前项目从“功能已基本成形”收口到“v1.0 可发布、可部署、可二次开发”的状态。

当前项目已经具备登录、用户、RBAC、菜单、部门、字典、参数、日志、文件、通知、站内消息、仪表盘、Items、OpenAPI、Docker 等基础能力。后续实施重点不是继续堆新模块，而是把这些模块做成稳定闭环：

- 初始化数据稳定可重复。
- 权限码、菜单、前端按钮和后端接口一致。
- 页面体验一致，关键路径无阻塞问题。
- API 契约稳定，生成类型可用。
- 核心测试可持续运行。
- Docker Compose 最小部署可验证。
- 文档与实际实现一致。

## 3. 总体原则

### 3.1 先收口，后扩展

v1.0 只做后台基座必需能力，不实现岗位、在线用户、对象存储、代码生成、定时任务、在线国际化、OAuth2、多租户、BPM、CRM/ERP/AI。

### 3.2 后端权限是最终边界

所有管理接口必须由后端 `require_permission("<permission_code>")` 控制。前端菜单和按钮隐藏只做体验优化。

### 3.3 每个模块必须闭环

模块完成定义：

- 模型和迁移存在。
- API 可用。
- 权限码接入。
- 默认菜单或入口配置完整。
- 前端页面可操作。
- 测试覆盖核心正向和越权场景。
- 文档更新。

### 3.4 小步验证

每个阶段结束必须运行本阶段验收命令。不得把构建、测试、部署问题留到最后集中处理。

### 3.5 不照搬 Litchi

参考 Litchi 的成熟模块边界和页面组织，但当前项目以 FastAPI + Vben 的轻中量后台基座为目标。Litchi 的平台级能力进入路线图，不进入 v1.0 阻塞范围。

## 4. 角色分工

| 角色 | 职责 |
| --- | --- |
| Tech Lead | 范围控制、技术方案确认、代码 review、发布决策 |
| Backend | 模型、迁移、API、权限、初始化、测试 |
| Frontend | 页面、路由、菜单、权限按钮、API wrapper、构建 |
| QA | 功能验收、权限矩阵、E2E、回归测试 |
| DevOps | Compose、环境变量、部署文档、安全检查 |
| Docs | README、模块指南、API 契约、发布说明 |

单人推进时，按本文里程碑顺序执行即可。

## 5. 版本与里程碑

| 里程碑 | 目标 | 建议周期 | 产出 |
| --- | --- | --- | --- |
| M0 | 基线盘点和验收环境 | 0.5-1 天 | 当前问题清单、可运行验证命令 |
| M1 | 初始化、权限和契约收口 | 1-2 天 | 幂等种子、权限清单、OpenAPI 稳定 |
| M2 | 系统管理模块打磨 | 2-3 天 | 用户、角色、菜单、部门、字典、参数闭环 |
| M3 | 审计、文件、通知闭环 | 2-3 天 | 日志、文件、公告、消息稳定可用 |
| M4 | Items 范例和开发者体验 | 1-2 天 | 可复制业务模块范式、导入导出范例 |
| M5 | 测试、E2E、CI 收口 | 1-2 天 | 后端测试、前端构建、关键 E2E |
| M6 | Docker、文档、发布打磨 | 1-2 天 | Compose 验证、README、发布清单 |

整体建议周期：8-15 个工作日，视现有缺陷数量浮动。

## 6. M0 基线盘点和验收环境

### 6.1 目标

确认当前代码能否在本地稳定启动、测试、构建，并产出待修复问题清单。

### 6.2 任务清单

| 编号 | 任务 | 涉及范围 | 产出 | 验收 |
| --- | --- | --- | --- | --- |
| M0-01 | 记录当前 git 状态 | 根目录 | 变更文件清单 | `git status --short` 输出已保存 |
| M0-02 | 检查环境变量 | `.env.example`、`.env` | 缺失配置清单 | 本地启动不因配置缺失失败 |
| M0-03 | 后端依赖安装验证 | `backend/pyproject.toml` | 可运行后端环境 | `cd backend && uv sync` 成功 |
| M0-04 | 数据库迁移验证 | Alembic | 空库迁移结果 | `cd backend && uv run alembic upgrade head` 成功 |
| M0-05 | 初始化数据验证 | `backend/app/initial_data.py` | 默认数据结果 | `cd backend && uv run python -m app.initial_data` 成功 |
| M0-06 | 后端测试基线 | `backend/tests` | 测试结果 | `cd backend && uv run pytest` 记录通过/失败 |
| M0-07 | 前端依赖和构建验证 | `frontend` | 构建结果 | `cd frontend && pnpm install && pnpm build` 记录通过/失败 |
| M0-08 | API 生成验证 | OpenAPI、前端 generated | 类型生成结果 | `pnpm generate:api` 或项目实际命令可运行 |
| M0-09 | Compose 验证 | `compose.yml` | 启动结果 | `docker compose up --build` 可启动核心服务 |

### 6.3 输出物

- `docs/implementation-issues.md`，记录 M0 发现的问题。若不新增文件，则在当前任务看板或 issue 中记录。
- 一份必须修复和可延后修复的分类清单。

### 6.4 退出标准

- 明确哪些测试/构建失败。
- 明确失败原因属于功能缺陷、环境问题还是文档问题。
- 后续 M1-M6 任务可以基于清单推进。

## 7. M1 初始化、权限和契约收口

### 7.1 目标

把 v1.0 最容易漂移的三件事收住：初始化数据、权限码、API 契约。

### 7.2 后端任务

| 编号 | 任务 | 涉及文件 | 实施要点 | 验收标准 |
| --- | --- | --- | --- | --- |
| M1-BE-01 | 梳理权限码清单 | `backend/app/api/routes/*`、`backend/app/core/db.py`、`docs/rbac.md` | 用 `rg "require_permission"` 提取后端权限码，对比种子菜单按钮权限 | 所有后端权限码都能在 `Menu.permission_code` 中初始化 |
| M1-BE-02 | 补齐默认菜单 | `backend/app/core/db.py` | 确认 dashboard、system、logs、files、notices、messages、items 都有菜单入口 | 默认管理员登录后能看到 v1.0 全部菜单 |
| M1-BE-03 | 补齐按钮权限 | `backend/app/core/db.py` | 对 create/update/delete/upload/publish/read 等操作补按钮权限 | 前端关键按钮均有权限码可用 |
| M1-BE-04 | 初始化幂等校验 | `ensure_*` 函数、测试 | 对角色、菜单、字典、参数重复初始化做测试 | 连续执行初始化两次无重复数据 |
| M1-BE-05 | 内置数据保护 | roles、menus、settings 路由 | `is_system=True` 角色和参数删除/关键字段更新受限 | 删除系统角色、系统参数被拒绝 |
| M1-BE-06 | 统一分页边界 | 所有列表接口 | `page >= 1`，`page_size` 有最大值，返回结构一致 | 列表接口均返回 `items/total/page/page_size` |
| M1-BE-07 | 统一错误策略 | `app/main.py`、路由异常 | 确认 401/403/404/409/422 响应前端可稳定处理 | API 契约文档与实际响应一致 |
| M1-BE-08 | OpenAPI 稳定检查 | OpenAPI schema | 修复 response_model 缺失或类型不准 | 前端类型生成无错误 |

### 7.3 前端任务

| 编号 | 任务 | 涉及文件 | 实施要点 | 验收标准 |
| --- | --- | --- | --- | --- |
| M1-FE-01 | 权限码使用清单 | `frontend/apps/web-antd/src` | 搜索 `authority`、`hasAccess`、按钮权限判断 | 前端权限码全部存在于后端清单 |
| M1-FE-02 | 菜单加载一致性 | router、store、api/core/menu.ts | 确认登录后使用 `/menus/me`，兜底路由只保留核心页 | 普通用户只看到授权菜单 |
| M1-FE-03 | 403/401 处理 | request、router guard | 401 退出登录，403 显示无权限或提示 | 越权请求体验清晰 |
| M1-FE-04 | 生成类型同步 | `src/api/generated` | 重新生成并修正 wrapper 类型 | TS 类型无红线 |
| M1-FE-05 | 菜单 component 映射检查 | router 动态加载逻辑 | 后端 component 与实际 vue 文件路径一致 | 动态路由刷新后可打开页面 |

### 7.4 测试任务

| 编号 | 场景 | 验收 |
| --- | --- | --- |
| M1-QA-01 | 默认管理员登录 | 可访问全部 v1.0 菜单 |
| M1-QA-02 | 普通用户登录 | 仅显示已授权菜单 |
| M1-QA-03 | 普通用户直连无权限接口 | 返回 403 |
| M1-QA-04 | 初始化重复执行 | 角色、菜单、字典、参数数量不重复膨胀 |
| M1-QA-05 | API 类型生成 | 前端生成类型成功且构建通过 |

### 7.5 退出标准

- 权限码清单、初始化菜单、前端按钮、后端依赖四者一致。
- OpenAPI 生成成功。
- 默认管理员和普通用户权限行为符合预期。

## 8. M2 系统管理模块打磨

### 8.1 目标

把用户、角色、菜单、部门、字典、系统参数这些后台基础模块打磨到可交付状态。

### 8.2 用户管理

| 编号 | 任务 | 涉及范围 | 验收标准 |
| --- | --- | --- | --- |
| M2-USER-01 | 用户列表筛选完善 | 后端 `/users`、前端用户页 | 支持邮箱/姓名/状态/部门筛选，分页正确 |
| M2-USER-02 | 用户表单校验 | 前后端 | 邮箱唯一、密码长度、部门有效性、角色有效性有明确错误 |
| M2-USER-03 | 用户角色分配 | `/users/{id}/roles`、前端表单 | 创建/编辑用户可分配多个角色 |
| M2-USER-04 | 超管保护 | 用户更新/删除 | 不能删除或禁用最后一个超级管理员 |
| M2-USER-05 | 重置密码 | 后端 API、前端弹窗 | 重置成功后旧密码不可用，新密码可登录 |

### 8.3 角色管理

| 编号 | 任务 | 涉及范围 | 验收标准 |
| --- | --- | --- | --- |
| M2-ROLE-01 | 角色 CRUD 稳定 | `/roles`、角色页 | 列表、新增、编辑、删除可用 |
| M2-ROLE-02 | 系统角色保护 | `/roles/{id}` | `is_system=True` 角色不能被删除或破坏 code |
| M2-ROLE-03 | 分配菜单权限 | `/roles/{id}/menus`、权限树 | 保存后用户重新登录或刷新权限生效 |
| M2-ROLE-04 | 角色启停 | 角色模型、权限依赖 | 禁用角色不继续授予权限，并有回归测试覆盖 |

### 8.4 菜单管理

| 编号 | 任务 | 涉及范围 | 验收标准 |
| --- | --- | --- | --- |
| M2-MENU-01 | 菜单树展示 | 后端 `/menus`、菜单页 | 目录/菜单/按钮层级正确 |
| M2-MENU-02 | 菜单类型规则 | 表单、后端校验 | 目录、菜单、按钮字段差异清晰 |
| M2-MENU-03 | 父子循环校验 | 后端更新接口 | 不能把自己或后代设为父级 |
| M2-MENU-04 | 删除保护 | 后端删除接口 | 有子菜单或角色绑定时删除策略明确 |
| M2-MENU-05 | 动态路由验证 | 前端动态路由 | 新增菜单后刷新可加载合法页面 |

### 8.5 部门管理

| 编号 | 任务 | 涉及范围 | 验收标准 |
| --- | --- | --- | --- |
| M2-DEPT-01 | 部门树展示 | `/departments`、部门页 | 多级部门显示正确 |
| M2-DEPT-02 | 部门 code 唯一 | 后端校验 | 重复 code 返回明确错误 |
| M2-DEPT-03 | 父子循环校验 | 后端更新接口 | 不能把自己或后代设为父级 |
| M2-DEPT-04 | 删除保护 | 后端删除接口 | 有子部门或用户时不能误删 |
| M2-DEPT-05 | 用户筛选联动 | 用户管理页 | 点击/选择部门可筛用户 |

### 8.6 字典管理

| 编号 | 任务 | 涉及范围 | 验收标准 |
| --- | --- | --- | --- |
| M2-DICT-01 | 字典类型 CRUD | 后端、字典页 | 类型新增、编辑、删除可用 |
| M2-DICT-02 | 字典项 CRUD | 后端、字典项区域 | 字典项新增、编辑、删除可用 |
| M2-DICT-03 | 唯一性校验 | 后端 | type code 唯一，同类型 item value 唯一 |
| M2-DICT-04 | 启停行为 | 后端查询、前端选择项 | 禁用项不出现在业务选择项中 |
| M2-DICT-05 | 颜色展示 | 前端表格 | 字典项 color 能用于 Tag 展示 |

### 8.7 系统参数

| 编号 | 任务 | 涉及范围 | 验收标准 |
| --- | --- | --- | --- |
| M2-SET-01 | 参数列表分组 | `/settings`、参数页 | 可按 group 筛选或分组展示 |
| M2-SET-02 | 类型化编辑 | 前端表单 | string/number/boolean/json 有合适输入控件 |
| M2-SET-03 | JSON 校验 | 后端更新接口 | 非法 JSON 返回明确错误 |
| M2-SET-04 | 公开参数 | `/settings/public` | 只返回 `is_public=True` 参数 |
| M2-SET-05 | 系统参数保护 | 后端 | `is_system=True` 关键参数不能误删或改 key |

### 8.8 M2 验收命令

```powershell
cd D:\project\fastapi-vue-vben-admin\backend
uv run pytest tests/api/routes/test_users.py tests/api/routes/test_rbac.py tests/api/routes/test_system_config.py

cd D:\project\fastapi-vue-vben-admin\frontend
pnpm build
```

### 8.9 退出标准

- 系统管理菜单下所有页面可正常增删改查。
- 普通用户无法访问系统管理接口。
- 页面无明显 Mock 数据和死入口。
- 后端测试覆盖核心权限和保护规则。

## 9. M3 审计、文件、通知闭环

### 9.1 目标

补齐生产后台常用的审计追踪、附件管理、公告消息能力。

### 9.2 登录日志

| 编号 | 任务 | 涉及范围 | 验收标准 |
| --- | --- | --- | --- |
| M3-LOGINLOG-01 | 成功日志 | 登录接口、`LoginLog` | 登录成功记录 user/email/ip/ua/status |
| M3-LOGINLOG-02 | 失败日志 | 登录接口 | 密码错误、禁用用户等失败场景有记录 |
| M3-LOGINLOG-03 | 查询筛选 | `/logs/login`、前端页面 | 支持邮箱、状态、时间筛选 |
| M3-LOGINLOG-04 | 隐私控制 | 登录响应、日志字段 | 登录失败不向用户暴露账号枚举信息 |

### 9.3 操作日志

| 编号 | 任务 | 涉及范围 | 验收标准 |
| --- | --- | --- | --- |
| M3-OPLOG-01 | 中间件记录 | `backend/app/audit.py` | POST/PATCH/PUT/DELETE 产生操作日志 |
| M3-OPLOG-02 | 排除规则 | `should_log_operation` | GET、日志查询、敏感认证路径不记录 |
| M3-OPLOG-03 | 脱敏策略 | request/response summary | password/token/authorization 不入库 |
| M3-OPLOG-04 | 查询筛选 | `/logs/operation`、前端页面 | 支持模块、动作、状态码、时间筛选 |
| M3-OPLOG-05 | 错误操作记录 | 中间件 | 4xx/5xx 修改请求也能记录状态码和耗时 |

### 9.4 文件管理

| 编号 | 任务 | 涉及范围 | 验收标准 |
| --- | --- | --- | --- |
| M3-FILE-01 | 上传限制 | `storage.py`、`/files/upload` | 超大小、非法扩展名返回明确错误 |
| M3-FILE-02 | 文件列表 | `/files`、文件页 | 展示名称、类型、大小、上传人、时间 |
| M3-FILE-03 | 下载授权 | `/files/{id}/download` | 私有文件需要登录和权限 |
| M3-FILE-04 | 删除一致性 | `/files/{id}` | 删除数据库记录同时删除本地文件 |
| M3-FILE-05 | 路径安全 | `get_local_file_path` | 路径穿越被阻止 |
| M3-FILE-06 | 头像上传 | `/files/avatar`、个人中心 | 当前用户可上传头像并更新 `avatar_url` |

### 9.5 通知公告和站内消息

| 编号 | 任务 | 涉及范围 | 验收标准 |
| --- | --- | --- | --- |
| M3-NOTICE-01 | 公告 CRUD | `/notices`、公告页 | 草稿公告可新增、编辑、删除 |
| M3-NOTICE-02 | 发布公告 | `/notices/{id}/publish` | 发布后生成用户消息 |
| M3-NOTICE-03 | 下线公告 | `/notices/{id}/offline` | 下线后不在当前公告中出现 |
| M3-NOTICE-04 | 消息列表 | `/messages/me`、消息页 | 用户只能看到自己的消息 |
| M3-NOTICE-05 | 标记已读 | `/messages/{id}/read` | 单条已读、全部已读可用 |
| M3-NOTICE-06 | 未读数 | 顶部消息入口 | 未读数准确刷新 |

### 9.6 M3 验收命令

```powershell
cd D:\project\fastapi-vue-vben-admin\backend
uv run pytest tests/api/routes/test_audit_logs.py tests/api/routes/test_files.py tests/api/routes/test_notices.py

cd D:\project\fastapi-vue-vben-admin\frontend
pnpm build
```

### 9.7 退出标准

- 登录和关键修改操作可审计。
- 文件上传、下载、删除、头像上传可用。
- 公告发布能形成用户站内消息。
- 敏感信息不进入日志明文。

## 10. M4 Items 范例和开发者体验

### 10.1 目标

把 Items 做成开发者可以复制的标准业务模块范例。

### 10.2 后端任务

| 编号 | 任务 | 涉及范围 | 验收标准 |
| --- | --- | --- | --- |
| M4-BE-01 | Items CRUD 收口 | `items.py`、`crud.py`、`models.py` | 列表、详情、新增、编辑、删除稳定 |
| M4-BE-02 | Items 权限 | `business:item:*` | list/create/update/delete 全部后端校验 |
| M4-BE-03 | Items 导出 | 导出接口 | 返回 CSV/XLSX，字段和文档一致 |
| M4-BE-04 | Items 导入 | 导入接口 | 返回总数、成功数、失败数、失败原因 |
| M4-BE-05 | Items 测试 | `test_items.py` | CRUD、权限、导入导出测试通过 |

### 10.3 前端任务

| 编号 | 任务 | 涉及范围 | 验收标准 |
| --- | --- | --- | --- |
| M4-FE-01 | 列表页范式 | `views/items/index.vue` | 查询区、工具栏、表格、分页、操作列完整 |
| M4-FE-02 | 表单范式 | `views/items/modules/form.vue` | 新增/编辑复用同一表单 |
| M4-FE-03 | 导入弹窗 | `views/items/modules/import.vue` | 上传模板、错误提示、结果展示 |
| M4-FE-04 | 导出按钮 | Items 页 | Blob 下载正确，权限控制正确 |
| M4-FE-05 | 复制指南 | 文档 | 新增业务模块步骤清楚 |

### 10.4 文档任务

| 编号 | 任务 | 产出 |
| --- | --- | --- |
| M4-DOC-01 | 新增模块指南 | 更新或新增 `docs/module-guide.md` |
| M4-DOC-02 | API 示例 | 更新 `docs/api-contract.md` |
| M4-DOC-03 | 权限示例 | 更新 `docs/rbac.md` |

### 10.5 退出标准

- Items 是一个完整可复制的 CRUD 范例。
- 开发者按文档可在 1 小时内复制一个简单业务模块。
- Items 页面和 API 不依赖 Mock 数据。

## 11. M5 测试、E2E、CI 收口

### 11.1 目标

建立 v1.0 发布门槛，避免“能跑一次”和“可维护发布”之间断层。

### 11.2 后端测试补齐

| 编号 | 测试主题 | 覆盖点 |
| --- | --- | --- |
| M5-BE-01 | 登录认证 | 成功、失败、禁用用户、重置密码 |
| M5-BE-02 | 权限矩阵 | 未登录、普通用户、管理员、超级管理员 |
| M5-BE-03 | 初始化幂等 | 重复 seed 不重复插入 |
| M5-BE-04 | 系统管理 | 用户、角色、菜单、部门、字典、参数 |
| M5-BE-05 | 审计日志 | 登录日志、操作日志、敏感字段 |
| M5-BE-06 | 文件 | 上传限制、下载、删除、路径安全 |
| M5-BE-07 | 通知消息 | 发布、下线、消息已读 |
| M5-BE-08 | Items | CRUD、导入、导出、越权 |

### 11.3 前端验证

| 编号 | 验证项 | 验收 |
| --- | --- | --- |
| M5-FE-01 | TypeScript | typecheck 通过 |
| M5-FE-02 | Build | `pnpm build` 通过 |
| M5-FE-03 | Login Flow | 登录后菜单、权限、个人信息正常 |
| M5-FE-04 | System Flow | 用户、角色、菜单、部门可操作 |
| M5-FE-05 | File Flow | 上传、下载、删除正常 |
| M5-FE-06 | Notice Flow | 发布公告、查看消息、标记已读正常 |
| M5-FE-07 | Unauthorized Flow | 普通用户看不到系统菜单，直连页面/接口被拦截 |

### 11.4 E2E 场景

| 编号 | 场景 | 步骤 | 期望 |
| --- | --- | --- | --- |
| M5-E2E-01 | 管理员登录 | 登录、加载菜单、进入仪表盘 | 成功 |
| M5-E2E-02 | 创建角色授权 | 新建角色、分配 Items 权限 | 保存成功 |
| M5-E2E-03 | 创建普通用户 | 新建用户、绑定角色 | 用户可登录 |
| M5-E2E-04 | 普通用户权限 | 普通用户登录 | 仅看到授权菜单 |
| M5-E2E-05 | 文件上传 | 上传合法文件、下载、删除 | 成功 |
| M5-E2E-06 | 公告消息 | 发布公告、用户查看消息 | 消息出现且可已读 |

当前仓库已补充 Playwright 用例覆盖管理员登录、Items CRUD、用户 CRUD、文件上传/下载/删除、公告发布生成消息并查看已读、受限用户菜单和管理接口 403。

### 11.5 CI 要求

CI 至少包含：

- 后端 lint 或格式检查。
- 后端测试。
- 前端 typecheck。
- 前端 build。
- 可选 CI E2E；本地发布前必须跑关键 E2E。

### 11.6 退出标准

- 发布分支所有 CI 通过。
- 权限矩阵测试通过。
- 关键 E2E 通过或有明确手工验收记录。

## 12. M6 Docker、文档、发布打磨

### 12.1 目标

让陌生用户按 README 能启动、能登录、能二次开发。

### 12.2 Docker 和部署任务

| 编号 | 任务 | 涉及范围 | 验收标准 |
| --- | --- | --- | --- |
| M6-OPS-01 | Compose 本地启动 | `compose.yml`、`compose.override.yml` | `docker compose up --build` 后前后端可访问 |
| M6-OPS-02 | 数据持久化 | db volume、uploads volume | 重启容器数据和文件不丢 |
| M6-OPS-03 | 迁移和初始化 | backend entrypoint/scripts | 空库启动后可迁移并初始化 |
| M6-OPS-04 | 环境变量完整性 | `.env.example` | 覆盖数据库、密钥、CORS、邮件、上传 |
| M6-OPS-05 | 生产安全检查 | `config.py`、部署文档 | 非 local 环境默认密钥会报错 |
| M6-OPS-06 | 健康检查 | `/utils/health-check` | 容器健康检查或文档说明可用 |

### 12.3 文档任务

| 编号 | 文档 | 内容 |
| --- | --- | --- |
| M6-DOC-01 | README | 项目定位、截图、快速开始、默认账号、常用命令 |
| M6-DOC-02 | `docs/development.md` | 本地开发、目录结构、API 生成、测试 |
| M6-DOC-03 | `docs/deployment.md` | Compose 部署、环境变量、反向代理、备份 |
| M6-DOC-04 | `docs/api-contract.md` | 错误响应、分页、认证、权限 |
| M6-DOC-05 | `docs/rbac.md` | 权限模型、权限码、菜单类型、默认角色 |
| M6-DOC-06 | `docs/module-guide.md` | 如何复制 Items 新增业务模块 |
| M6-DOC-07 | CHANGELOG | v1.0 变更摘要 |

### 12.4 发布前人工验收

| 编号 | 项目 | 验收 |
| --- | --- | --- |
| M6-QA-01 | 全新环境启动 | 按 README 从零启动成功 |
| M6-QA-02 | 默认管理员 | 可登录并看到全部菜单 |
| M6-QA-03 | 系统管理 | 用户、角色、菜单、部门、字典、参数可用 |
| M6-QA-04 | 审计日志 | 登录和操作日志有记录 |
| M6-QA-05 | 文件 | 上传、下载、删除可用 |
| M6-QA-06 | 通知消息 | 发布公告后用户收到消息 |
| M6-QA-07 | Items | CRUD、导入、导出可用 |
| M6-QA-08 | 普通用户 | 无权限菜单不可见，接口越权 403 |

### 12.5 退出标准

- README 可指导陌生用户启动。
- Docker Compose 最小部署可用。
- 所有发布前人工验收通过。
- 文档与实现一致。

## 13. 总任务看板

### 13.1 P0 必须完成

| 编号 | 任务 | 里程碑 |
| --- | --- | --- |
| P0-01 | 权限码清单和初始化菜单一致 | M1 |
| P0-02 | 初始化幂等测试 | M1 |
| P0-03 | OpenAPI 类型生成成功 | M1 |
| P0-04 | 用户、角色、菜单、部门闭环 | M2 |
| P0-05 | 普通用户越权返回 403 | M1/M2 |
| P0-06 | 后端核心测试通过 | M5 |
| P0-07 | 前端构建通过 | M5 |
| P0-08 | Docker Compose 可启动 | M6 |
| P0-09 | README 快速开始可用 | M6 |

### 13.2 P1 应完成

| 编号 | 任务 | 里程碑 |
| --- | --- | --- |
| P1-01 | 字典、参数页面体验打磨 | M2 |
| P1-02 | 登录日志和操作日志筛选 | M3 |
| P1-03 | 文件下载和删除一致性 | M3 |
| P1-04 | 公告发布和消息已读闭环 | M3 |
| P1-05 | Items 导入导出范例 | M4 |
| P1-06 | 模块开发指南 | M4 |
| P1-07 | 关键 E2E | M5 |

### 13.3 P2 可延后到 v1.1+

| 编号 | 任务 | 原因 |
| --- | --- | --- |
| P2-01 | 岗位管理 | 非 v1.0 必需 |
| P2-02 | 在线用户和强制下线 | 需要会话模型 |
| P2-03 | MinIO/S3 对象存储 | 需要存储配置模型 |
| P2-04 | 代码生成 | 需要单独产品设计 |
| P2-05 | 定时任务 | 需要确定调度架构 |
| P2-06 | 在线国际化 | 需要翻译数据模型和缓存策略 |
| P2-07 | OAuth2/SSO | 企业登录专项 |
| P2-08 | 多租户 | v2.0 平台化能力 |

## 14. 验收命令清单

### 14.1 后端

```powershell
cd D:\project\fastapi-vue-vben-admin\backend
uv sync
uv run alembic upgrade head
uv run python -m app.initial_data
uv run pytest
```

### 14.2 前端

```powershell
cd D:\project\fastapi-vue-vben-admin\frontend
pnpm install
pnpm generate:api
pnpm build
```

如果项目实际命令不同，以 `frontend/package.json` 和根目录 `package.json` 为准，并同步更新 README。

### 14.3 Docker

```powershell
cd D:\project\fastapi-vue-vben-admin
docker compose up --build
```

### 14.4 手工冒烟

| 步骤 | 验收 |
| --- | --- |
| 打开前端 | 登录页正常 |
| 默认管理员登录 | 进入仪表盘 |
| 查看菜单 | 系统管理、日志、文件、公告、消息、Items 可见 |
| 新建角色 | 成功 |
| 分配权限 | 成功 |
| 新建普通用户 | 成功 |
| 普通用户登录 | 菜单受限 |
| 上传文件 | 成功 |
| 发布公告 | 用户收到消息 |
| 查看日志 | 有登录和操作记录 |

## 15. 风险、阻塞和处理策略

| 风险 | 触发信号 | 处理策略 |
| --- | --- | --- |
| 权限码不一致 | 前端按钮有权限但接口 403，或接口有权限但菜单没有 | M1 先做权限码清单，新增测试 |
| 初始化数据污染 | 重复启动后菜单/角色重复 | 所有种子使用 `ensure_*`，加幂等测试 |
| 动态路由打不开 | 后端 component 和前端文件不匹配 | M1 建 component 映射检查 |
| 操作日志泄密 | 日志出现 password/token | M3 做脱敏测试，敏感路径排除 |
| 文件路径穿越 | 构造 `../` 下载 | 使用 `resolve` 校验并加测试 |
| 前端 build 迟迟失败 | generated 类型和 wrapper 不匹配 | M1 固定 OpenAPI，M5 前不再做破坏性接口 |
| Docker 环境不可复现 | 本地可跑，容器不可跑 | M6 单独做空库 Compose 验收 |
| 范围继续膨胀 | 想加入岗位、在线用户、对象存储、多租户 | 移入 P2/v1.x，不阻塞 v1.0 |

## 16. 发布准入标准

只有满足以下条件，才能标记 v1.0 ready：

- P0 任务全部完成。
- P1 任务无阻塞缺陷，未完成项有明确记录和版本归属。
- `uv run pytest` 通过。
- `pnpm build` 通过。
- Docker Compose 最小部署通过；若本机未安装 Docker CLI，必须在具备 Docker 的环境或 CI 中补验。
- 默认管理员可登录。
- 普通用户权限隔离验证通过。
- 核心模块手工冒烟通过。
- README、PRD、TRD、RBAC、API 契约、模块指南与实现一致。
- `.env.example` 完整，真实 `.env` 未提交。
- CHANGELOG 有 v1.0 摘要。

## 17. 建议执行顺序

实际推进时按下面顺序最稳：

1. 先跑 M0，拿到真实失败清单。
2. 先修 M1 权限、初始化和 OpenAPI，因为它们会影响所有模块。
3. 再做 M2 系统管理，确保用户、角色、菜单、部门这些根基稳定。
4. 然后做 M3 审计、文件、通知，补齐生产后台通用能力。
5. 接着做 M4，把 Items 打造成开发者复制范例。
6. 最后做 M5/M6 测试、Compose、文档和发布。

不要在 M1 未完成前推进岗位、在线用户、对象存储、代码生成、多租户等扩展能力。v1.0 的胜利条件是“稳定可用”，不是“菜单最多”。
