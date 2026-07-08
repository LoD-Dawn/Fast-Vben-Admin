import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    component: () => import('#/views/files/index.vue'),
    meta: {
      authority: ['system:file:list'],
      icon: 'lucide:folder',
      order: 25,
      title: 'menu.files',
    },
    name: 'Files',
    path: '/files',
  },
];

export default routes;
