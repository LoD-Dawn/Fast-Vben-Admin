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
    <div class="flex flex-col lg:flex-row">
      <Card class="w-full lg:w-2/5" :loading="loading" title="个人中心">
        <ProfileUser :profile="profile" @success="loadProfile" />
      </Card>

      <Card
        class="mt-3 min-w-0 w-full lg:ml-3 lg:mt-0 lg:w-3/5"
        :loading="loading"
      >
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
