import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    meta: {
      icon: 'lucide:settings',
      order: 10,
      title: 'menu.system',
    },
    name: 'System',
    path: '/system',
    children: [
      {
        component: () => import('#/views/system/users/index.vue'),
        meta: {
          authority: ['system:user:list'],
          icon: 'lucide:users',
          title: 'menu.systemUsers',
        },
        name: 'SystemUsers',
        path: 'users',
      },
      {
        component: () => import('#/views/system/roles/index.vue'),
        meta: {
          authority: ['system:role:list'],
          icon: 'lucide:shield-check',
          title: 'menu.systemRoles',
        },
        name: 'SystemRoles',
        path: 'roles',
      },
      {
        component: () => import('#/views/system/menus/index.vue'),
        meta: {
          authority: ['system:menu:list'],
          icon: 'lucide:menu',
          title: 'menu.systemMenus',
        },
        name: 'SystemMenus',
        path: 'menus',
      },
      {
        component: () => import('#/views/system/departments/index.vue'),
        meta: {
          authority: ['system:department:list'],
          icon: 'lucide:building-2',
          title: 'menu.systemDepartments',
        },
        name: 'SystemDepartments',
        path: 'departments',
      },
      {
        component: () => import('#/views/system/dictionaries/index.vue'),
        meta: {
          authority: ['system:dict:list'],
          icon: 'lucide:book-open',
          title: 'menu.systemDictionaries',
        },
        name: 'SystemDictionaries',
        path: 'dictionaries',
      },
      {
        component: () => import('#/views/system/settings/index.vue'),
        meta: {
          authority: ['system:setting:list'],
          icon: 'lucide:sliders-horizontal',
          title: 'menu.systemSettings',
        },
        name: 'SystemSettings',
        path: 'settings',
      },
    ],
  },
];

export default routes;
