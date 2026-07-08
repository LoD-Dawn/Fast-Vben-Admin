import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    component: () => import('#/views/notices/index.vue'),
    meta: {
      authority: ['system:notice:list'],
      icon: 'lucide:megaphone',
      order: 26,
      title: 'menu.notices',
    },
    name: 'Notices',
    path: '/notices',
  },
  {
    component: () => import('#/views/messages/index.vue'),
    meta: {
      authority: ['personal:message:list'],
      icon: 'lucide:mail',
      order: 27,
      title: 'menu.messages',
    },
    name: 'Messages',
    path: '/messages',
  },
];

export default routes;
