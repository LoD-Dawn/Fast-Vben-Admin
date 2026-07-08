<script lang="ts" setup>
import type { NotificationItem } from '@vben/layouts';

import type { UserMessageRecord } from '#/api';

import { computed, onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';

import { AuthenticationLoginExpiredModal } from '@vben/common-ui';
import { VBEN_DOC_URL, VBEN_GITHUB_URL } from '@vben/constants';
import { useWatermark } from '@vben/hooks';
import { BookOpenText, CircleHelp, SvgGithubIcon } from '@vben/icons';
import {
  BasicLayout,
  LockScreen,
  Notification,
  UserDropdown,
} from '@vben/layouts';
import { preferences, usePreferences } from '@vben/preferences';
import { useAccessStore, useUserStore } from '@vben/stores';
import { formatDateTime, openWindow } from '@vben/utils';

import { listMyMessagesApi, markMessageReadApi } from '#/api';
import { $t } from '#/locales';
import { useAuthStore } from '#/store';
import LoginForm from '#/views/_core/authentication/login.vue';

const notifications = ref<NotificationItem[]>([]);

function mapMessageToNotification(
  message: UserMessageRecord,
): NotificationItem {
  return {
    id: message.id,
    avatar: preferences.app.defaultAvatar,
    date: message.created_at ? formatDateTime(message.created_at) : '',
    isRead: message.is_read ?? false,
    message: message.content,
    title: message.title,
    link: '/messages',
  };
}

async function fetchNotifications() {
  try {
    const result = await listMyMessagesApi({ page: 1, page_size: 10 });
    notifications.value = result.items.map(mapMessageToNotification);
  } catch {
    notifications.value = [];
  }
}

onMounted(() => {
  void fetchNotifications();
});

const router = useRouter();
const userStore = useUserStore();
const authStore = useAuthStore();
const accessStore = useAccessStore();

watch(
  () => accessStore.accessToken,
  (token) => {
    if (token) {
      void fetchNotifications();
    } else {
      notifications.value = [];
    }
  },
);
const { destroyWatermark, updateWatermark } = useWatermark();
const { isDark } = usePreferences();
const showDot = computed(() =>
  notifications.value.some((item) => !item.isRead),
);

const menus = computed(() => [
  {
    handler: () => {
      router.push({ name: 'Profile' });
    },
    icon: 'lucide:user',
    text: $t('page.auth.profile'),
  },
  {
    handler: () => {
      openWindow(VBEN_DOC_URL, {
        target: '_blank',
      });
    },
    icon: BookOpenText,
    text: $t('ui.widgets.document'),
  },
  {
    handler: () => {
      openWindow(VBEN_GITHUB_URL, {
        target: '_blank',
      });
    },
    icon: SvgGithubIcon,
    text: 'GitHub',
  },
  {
    handler: () => {
      openWindow(`${VBEN_GITHUB_URL}/issues`, {
        target: '_blank',
      });
    },
    icon: CircleHelp,
    text: $t('ui.widgets.qa'),
  },
]);

const avatar = computed(() => {
  return userStore.userInfo?.avatar || preferences.app.defaultAvatar;
});

const userDescription = computed(
  () => userStore.userInfo?.username || userStore.userInfo?.realName || '',
);

async function handleLogout() {
  await authStore.logout(false);
}

async function handleNoticeClear() {
  const unreadItems = notifications.value.filter((item) => !item.isRead);
  await Promise.all(
    unreadItems.map((item) => markMessageReadApi(String(item.id))),
  );
  notifications.value = [];
}

async function markRead(id: number | string) {
  const item = notifications.value.find((item) => item.id === id);
  if (!item || item.isRead) {
    return;
  }
  try {
    await markMessageReadApi(String(id));
    item.isRead = true;
  } catch {
    // keep unread state on failure
  }
}

function remove(id: number | string) {
  notifications.value = notifications.value.filter((item) => item.id !== id);
}

async function handleMakeAll() {
  const unreadItems = notifications.value.filter((item) => !item.isRead);
  if (unreadItems.length === 0) {
    return;
  }
  try {
    await Promise.all(
      unreadItems.map((item) => markMessageReadApi(String(item.id))),
    );
    notifications.value.forEach((item) => {
      item.isRead = true;
    });
  } catch {
    await fetchNotifications();
  }
}

function viewAll() {
  router.push({ name: 'Messages' });
}

async function handleClick(item: NotificationItem) {
  if (item.id && !item.isRead) {
    await markRead(item.id);
  }
  if (item.link) {
    navigateTo(item.link, item.query, item.state);
  }
}

function navigateTo(
  link: string,
  query?: Record<string, any>,
  state?: Record<string, any>,
) {
  if (link.startsWith('http://') || link.startsWith('https://')) {
    // 外部链接，在新标签页打开
    window.open(link, '_blank');
  } else {
    // 内部路由链接，支持 query 参数和 state
    router.push({
      path: link,
      query: query || {},
      state,
    });
  }
}

watch(
  () => ({
    enable: preferences.app.watermark,
    content: preferences.app.watermarkContent,
    isDark: isDark.value,
  }),
  async ({ enable, content, isDark: isDarkValue }) => {
    if (enable) {
      const watermarkColor = isDarkValue
        ? 'rgba(255, 255, 255, 0.12)'
        : 'rgba(0, 0, 0, 0.12)';

      await updateWatermark({
        advancedStyle: {
          colorStops: [
            {
              color: watermarkColor,
              offset: 0,
            },
            {
              color: watermarkColor,
              offset: 1,
            },
          ],
          type: 'linear',
        },
        content:
          content ||
          `${userStore.userInfo?.username} - ${userStore.userInfo?.realName}`,
      });
    } else {
      destroyWatermark();
    }
  },
  {
    immediate: true,
  },
);
</script>

<template>
  <BasicLayout @clear-preferences-and-logout="handleLogout">
    <template #user-dropdown>
      <UserDropdown
        :avatar
        :menus
        :text="userStore.userInfo?.realName"
        :description="userDescription"
        tag-text="Pro"
        trigger="both"
        @logout="handleLogout"
        @clear-preferences-and-logout="handleLogout"
      />
    </template>
    <template #notification>
      <Notification
        :dot="showDot"
        :notifications="notifications"
        @clear="handleNoticeClear"
        @read="(item) => item.id && markRead(item.id)"
        @remove="(item) => item.id && remove(item.id)"
        @make-all="handleMakeAll"
        @on-click="handleClick"
        @view-all="viewAll"
      />
    </template>
    <template #extra>
      <AuthenticationLoginExpiredModal
        v-model:open="accessStore.loginExpired"
        :avatar
      >
        <LoginForm />
      </AuthenticationLoginExpiredModal>
    </template>
    <template #lock-screen>
      <LockScreen :avatar @to-login="handleLogout" />
    </template>
  </BasicLayout>
</template>
