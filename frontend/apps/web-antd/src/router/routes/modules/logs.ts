import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    meta: {
      icon: 'lucide:clipboard-list',
      order: 15,
      title: 'menu.logs',
    },
    name: 'Logs',
    path: '/logs',
    children: [
      {
        component: () => import('#/views/logs/login/index.vue'),
        meta: {
          authority: ['system:login-log:list'],
          icon: 'lucide:log-in',
          title: 'menu.loginLogs',
        },
        name: 'LoginLogs',
        path: 'login',
      },
      {
        component: () => import('#/views/logs/operation/index.vue'),
        meta: {
          authority: ['system:operation-log:list'],
          icon: 'lucide:history',
          title: 'menu.operationLogs',
        },
        name: 'OperationLogs',
        path: 'operation',
      },
    ],
  },
];

export default routes;
