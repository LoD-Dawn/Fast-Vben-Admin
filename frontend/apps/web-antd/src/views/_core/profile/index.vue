<script setup lang="ts">
import type { AuthApi } from '#/api';

import { onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';

import { Card, Tabs } from 'ant-design-vue';

import { getCurrentUserApi } from '#/api';

import ProfileBase from './base-setting.vue';
import ProfileUser from './modules/profile-user.vue';
import ProfilePasswordSetting from './password-setting.vue';
import ProfileSecuritySetting from './security-setting.vue';

const activeName = ref('basic');
const loading = ref(false);
const profile = ref<AuthApi.FastApiUser>();

async function loadProfile() {
  loading.value = true;
  try {
    profile.value = await getCurrentUserApi();
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  void loadProfile();
});
</script>

<template>
  <Page auto-content-height>
    <div
      class="grid grid-cols-1 items-start gap-4 xl:grid-cols-[minmax(400px,2fr)_minmax(0,3fr)]"
    >
      <Card class="h-full" :loading="loading" title="个人中心">
        <ProfileUser :profile="profile" @success="loadProfile" />
      </Card>

      <Card class="min-w-0" :loading="loading">
        <Tabs v-model:active-key="activeName" class="-mt-4">
          <Tabs.TabPane key="basic" tab="基本设置">
            <ProfileBase :profile="profile" @success="loadProfile" />
          </Tabs.TabPane>
          <Tabs.TabPane key="password" tab="修改密码">
            <ProfilePasswordSetting />
          </Tabs.TabPane>
          <Tabs.TabPane key="security" force-render tab="安全设置">
            <ProfileSecuritySetting />
          </Tabs.TabPane>
        </Tabs>
      </Card>
    </div>
  </Page>
</template>
