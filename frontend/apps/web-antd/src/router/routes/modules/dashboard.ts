import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    component: () => import('#/views/dashboard/analytics/index.vue'),
    meta: {
      affixTab: true,
      icon: 'lucide:layout-dashboard',
      keepAlive: true,
      order: -1,
      title: 'menu.dashboard',
    },
    name: 'Dashboard',
    path: '/dashboard',
  },
];

export default routes;
