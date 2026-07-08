import type { RouteRecordStringComponent } from '@vben/types';

import { getMyMenusApi } from './rbac';

interface BackendMenuRoute {
  component?: null | string;
  icon?: null | string;
  id?: string;
  name?: string;
  parent_id?: null | string;
  path?: string;
  permission_code?: null | string;
  route_name?: null | string;
  route_path?: null | string;
  sort?: number;
  title: string;
  type?: string;
}

function normalizeComponent(component?: null | string) {
  return component?.replace(/^#/, '');
}

/** 兼容数据库中仍使用中文标题的旧菜单数据 */
const LEGACY_MENU_TITLE_KEYS: Record<string, string> = {
  业务示例: 'menu.items',
  任务示例: 'menu.items',
  仪表盘: 'menu.dashboard',
  参数配置: 'menu.systemSettings',
  字典管理: 'menu.systemDictionaries',
  文件管理: 'menu.files',
  日志审计: 'menu.logs',
  操作日志: 'menu.operationLogs',
  用户管理: 'menu.systemUsers',
  登录日志: 'menu.loginLogs',
  示例资源: 'menu.items',
  系统管理: 'menu.system',
  菜单管理: 'menu.systemMenus',
  角色管理: 'menu.systemRoles',
  部门管理: 'menu.systemDepartments',
  我的消息: 'menu.messages',
  通知公告: 'menu.notices',
};

function resolveMenuTitle(title: string) {
  if (title.includes('.')) {
    return title;
  }
  return LEGACY_MENU_TITLE_KEYS[title] ?? title;
}

function toRoute(menu: BackendMenuRoute): RouteRecordStringComponent {
  return {
    children: [],
    component:
      normalizeComponent(menu.component) ||
      (menu.type === 'directory' ? 'BasicLayout' : ''),
    meta: {
      authority: menu.permission_code ? [menu.permission_code] : undefined,
      icon: menu.icon || undefined,
      order: menu.sort,
      title: resolveMenuTitle(menu.title),
    },
    name: menu.route_name || menu.name || menu.id,
    path: menu.route_path || menu.path || '/',
  };
}

/**
 * 获取用户所有菜单
 */
export async function getAllMenusApi() {
  const menus = (await getMyMenusApi()) as unknown as BackendMenuRoute[];
  const routeById = new Map<string, RouteRecordStringComponent>();
  const roots: RouteRecordStringComponent[] = [];

  for (const menu of menus.filter((item) => item.type !== 'button')) {
    if (!menu.id) continue;
    routeById.set(menu.id, toRoute(menu));
  }

  for (const menu of menus.filter((item) => item.type !== 'button')) {
    if (!menu.id) continue;
    const route = routeById.get(menu.id);
    if (!route) continue;
    if (menu.parent_id && routeById.has(menu.parent_id)) {
      const parent = routeById.get(menu.parent_id);
      parent?.children?.push(route);
    } else {
      roots.push(route);
    }
  }

  return roots;
}
