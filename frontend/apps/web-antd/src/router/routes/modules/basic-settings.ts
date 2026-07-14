import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    meta: {
      icon: 'lucide:settings-2',
      order: 15,
      title: 'menu.infrastructure',
    },
    name: 'BasicSettings',
    path: '/basic-settings',
    children: [
      {
        component: () => import('#/views/system/settings/index.vue'),
        meta: {
          authority: ['system:setting:list'],
          icon: 'lucide:sliders-horizontal',
          order: 10,
          title: 'menu.systemSettings',
        },
        name: 'SystemSettings',
        path: 'settings',
      },
      {
        meta: {
          icon: 'lucide:folder',
          order: 20,
          title: 'menu.files',
        },
        name: 'Files',
        path: 'files',
        children: [
          {
            component: () => import('#/views/files/channels/index.vue'),
            meta: {
              authority: ['system:file:channel:list'],
              icon: 'lucide:database',
              title: 'menu.fileChannels',
            },
            name: 'FileChannels',
            path: 'channels',
          },
          {
            component: () => import('#/views/files/config/index.vue'),
            meta: {
              authority: ['system:file:config:list'],
              icon: 'lucide:settings-2',
              title: 'menu.fileConfig',
            },
            name: 'FileConfig',
            path: 'config',
          },
          {
            component: () => import('#/views/files/index.vue'),
            meta: {
              authority: ['system:file:list'],
              icon: 'lucide:files',
              title: 'menu.fileList',
            },
            name: 'FileList',
            path: 'list',
          },
        ],
      },
    ],
  },
];

export default routes;
