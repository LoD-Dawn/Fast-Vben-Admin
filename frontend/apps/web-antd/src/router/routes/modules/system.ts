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
        component: () => import('#/views/system/posts/index.vue'),
        meta: {
          authority: ['system:post:list'],
          icon: 'lucide:briefcase-business',
          title: 'menu.systemPosts',
        },
        name: 'SystemPosts',
        path: 'posts',
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
        component: () => import('#/views/_core/router-view.vue'),
        meta: {
          icon: 'lucide:shield',
          order: 85,
          title: 'menu.oauth2',
        },
        name: 'OAuth2',
        path: 'oauth2',
        children: [
          {
            component: () => import('#/views/oauth2/clients/index.vue'),
            meta: {
              authority: ['system:oauth2-client:list'],
              icon: 'lucide:hard-drive',
              title: 'menu.oauth2Clients',
            },
            name: 'OAuth2Clients',
            path: 'clients',
          },
          {
            component: () => import('#/views/oauth2/tokens/index.vue'),
            meta: {
              authority: ['system:oauth2-token:list'],
              icon: 'lucide:key-round',
              title: 'menu.oauth2Tokens',
            },
            name: 'OAuth2Tokens',
            path: 'tokens',
          },
        ],
      },
      {
        component: () => import('#/views/_core/router-view.vue'),
        meta: {
          icon: 'lucide:rocket',
          order: 86,
          title: 'menu.socialLogin',
        },
        name: 'SocialLogin',
        path: 'social',
        children: [
          {
            component: () => import('#/views/social/clients/index.vue'),
            meta: {
              authority: ['system:social-client:list'],
              icon: 'lucide:settings-2',
              title: 'menu.socialClients',
            },
            name: 'SocialClients',
            path: 'clients',
          },
          {
            component: () => import('#/views/social/users/index.vue'),
            meta: {
              authority: ['system:social-user:list'],
              icon: 'lucide:users-round',
              title: 'menu.socialUsers',
            },
            name: 'SocialUsers',
            path: 'users',
          },
        ],
      },
      {
        meta: {
          icon: 'lucide:clipboard-list',
          order: 90,
          title: 'menu.logs',
        },
        name: 'Logs',
        path: 'logs',
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
      {
        meta: {
          icon: 'lucide:messages-square',
          order: 110,
          title: 'menu.messageCenter',
        },
        name: 'MessageCenter',
        path: 'message-center',
        children: [
          {
            component: () => import('#/views/notices/index.vue'),
            meta: {
              authority: ['system:notice:list'],
              icon: 'lucide:megaphone',
              title: 'menu.notices',
            },
            name: 'Notices',
            path: 'notices',
          },
          {
            component: () => import('#/views/messages/index.vue'),
            meta: {
              authority: ['personal:message:list'],
              icon: 'lucide:mail',
              title: 'menu.messages',
            },
            name: 'Messages',
            path: 'messages',
          },
          {
            component: () => import('#/views/_core/router-view.vue'),
            meta: {
              icon: 'lucide:inbox',
              title: 'menu.siteMessages',
            },
            name: 'SiteMessages',
            path: 'site-messages',
            children: [
              {
                component: () =>
                  import('#/views/site-messages/templates/index.vue'),
                meta: {
                  authority: ['system:site-message-template:list'],
                  icon: 'lucide:archive',
                  title: 'menu.siteMessageTemplates',
                },
                name: 'SiteMessageTemplates',
                path: 'templates',
              },
              {
                component: () =>
                  import('#/views/site-messages/messages/index.vue'),
                meta: {
                  authority: ['system:site-message:list'],
                  icon: 'lucide:edit-3',
                  title: 'menu.siteMessageList',
                },
                name: 'SiteMessageList',
                path: 'list',
              },
            ],
          },
          {
            component: () => import('#/views/_core/router-view.vue'),
            meta: {
              icon: 'lucide:message-square-more',
              title: 'menu.sms',
            },
            name: 'Sms',
            path: 'sms',
            children: [
              {
                component: () => import('#/views/sms/channels/index.vue'),
                meta: {
                  authority: ['system:sms-channel:list'],
                  icon: 'lucide:messages-square',
                  title: 'menu.smsChannels',
                },
                name: 'SmsChannels',
                path: 'channels',
              },
              {
                component: () => import('#/views/sms/templates/index.vue'),
                meta: {
                  authority: ['system:sms-template:list'],
                  icon: 'lucide:scroll-text',
                  title: 'menu.smsTemplates',
                },
                name: 'SmsTemplates',
                path: 'templates',
              },
              {
                component: () => import('#/views/sms/logs/index.vue'),
                meta: {
                  authority: ['system:sms-log:list'],
                  icon: 'lucide:send',
                  title: 'menu.smsLogs',
                },
                name: 'SmsLogs',
                path: 'logs',
              },
            ],
          },
          {
            component: () => import('#/views/_core/router-view.vue'),
            meta: {
              icon: 'lucide:mail',
              title: 'menu.mail',
            },
            name: 'Mail',
            path: 'mail',
            children: [
              {
                component: () => import('#/views/mail/accounts/index.vue'),
                meta: {
                  authority: ['system:mail-account:list'],
                  icon: 'lucide:mail-check',
                  title: 'menu.mailAccounts',
                },
                name: 'MailAccounts',
                path: 'accounts',
              },
              {
                component: () => import('#/views/mail/templates/index.vue'),
                meta: {
                  authority: ['system:mail-template:list'],
                  icon: 'lucide:scroll-text',
                  title: 'menu.mailTemplates',
                },
                name: 'MailTemplates',
                path: 'templates',
              },
              {
                component: () => import('#/views/mail/logs/index.vue'),
                meta: {
                  authority: ['system:mail-log:list'],
                  icon: 'lucide:send',
                  title: 'menu.mailLogs',
                },
                name: 'MailLogs',
                path: 'logs',
              },
            ],
          },
        ],
      },
    ],
  },
];

export default routes;
