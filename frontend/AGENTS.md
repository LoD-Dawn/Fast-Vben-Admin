# Frontend Agent Standard

本文件适用于 `frontend/` 下的所有修改，并补充仓库根目录 [AGENTS.md](../AGENTS.md)。

## 1. 应用边界

- 当前交付应用是 `apps/web-antd`，使用 Vue 3、TypeScript、Vite、Pinia、Vue Router、Vben 和 Ant Design Vue。
- 新业务模块代码进入 `apps/web-antd/src/modules/<module_code>`，不得继续增加全局业务 views、全局业务 API 或第二套模块注册机制。
- Platform 公共页面和客户端可以保留在现有 core 目录；可选业务模块不得被 Platform 或其他可选模块静态导入。
- 组件映射、模块初始化和可选工作台部件通过模块注册与 Build Manifest 装配。

## 2. API 与生成代码

- 后端 OpenAPI 是接口类型源。不要手工编辑 `src/api/generated` 或模块 `api/generated`。
- 修改后端 API/DTO 后，在仓库根目录运行 `pnpm generate:api -- --edition <edition>`。
- 模块页面只导入本模块生成客户端和 Platform 公共客户端，不导入其他可选模块客户端。
- 生成失败、命名冲突或契约不兼容必须修复源 Schema，不能在生成文件中打补丁。

## 3. Edition 与路由

- 前端实际启用模块由 Build Manifest 决定，不能用环境变量、菜单存在性或动态 import 猜测 Edition。
- 后端菜单 `component` 必须能在当前 Edition 的组件映射中解析；未知组件必须失败关闭或进入现有降级路径。
- Base 构建不得注册、预加载或展示 Items 运行入口；Items/Suite 只能加载 Manifest 包含的模块。
- Manifest schema、digest、source revision 或模块 OpenAPI digest 不兼容时，使用现有兼容性检查，不能静默忽略。

## 4. 权限与交互

- 页面、按钮、表格操作使用现有 `v-access:code`、`auth` 或访问组件；权限码必须与后端声明一致。
- 前端权限只控制可见性和交互，不替代后端校验。
- 对 401/403/404/409/503 使用现有错误处理和稳定错误码；模块未安装、未授权、租户停用和模块 degraded 必须保持可区分。
- 表单提交、删除、导入导出和长任务需要完整 loading、disabled、失败和重试状态，避免重复提交。

## 5. 组件与状态

- 优先复用项目组件、composable、store 和表格/表单模式，不复制基础能力。
- 模块私有状态保留在模块内；只有跨 Platform 的稳定状态才进入公共 store。
- 不在组件加载时产生隐藏的数据库同步、模块安装或权限写入副作用。
- 文案进入现有 locale 体系；不在多个页面复制同一业务枚举文本。
- 保持桌面和移动视口可用，文本不能溢出或遮挡操作，工具按钮使用项目已有图标和 tooltip 约定。

## 6. 前端验证

```powershell
pnpm frontend:typecheck
pnpm frontend:build
```

涉及 Edition、模块注册、路由或生成客户端时，还必须运行：

```powershell
pnpm build:edition -- --edition base
pnpm build:edition -- --edition items
pnpm build:edition -- --edition suite
```

涉及真实用户流程时运行对应 Playwright E2E，并检查浏览器控制台、网络错误、权限状态和响应式布局。不要只以 TypeScript 编译成功作为 UI 完成证据。
