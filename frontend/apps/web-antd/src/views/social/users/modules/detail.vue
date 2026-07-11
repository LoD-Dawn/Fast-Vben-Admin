<script lang="ts" setup>
import type { SocialUserRecord } from '#/api';

import { computed, ref } from 'vue';

import { useVbenDrawer } from '@vben/common-ui';

import { Descriptions, DescriptionsItem, Image, Tag } from 'ant-design-vue';

import { getSocialUserApi } from '#/api';

import { socialTypeOptions } from '../../clients/data';

const detail = ref<SocialUserRecord>();

function getSocialTypeLabel(type?: string) {
  return socialTypeOptions.find((item) => item.value === type)?.label || type;
}

const drawerTitle = computed(() => detail.value?.nickname || '社交用户详情');

const [Drawer, drawerApi] = useVbenDrawer({
  async onOpenChange(isOpen) {
    if (!isOpen) {
      detail.value = undefined;
      return;
    }
    const data = drawerApi.getData<SocialUserRecord>();
    if (!data?.id) return;
    drawerApi.lock();
    try {
      detail.value = await getSocialUserApi(data.id);
    } finally {
      drawerApi.unlock();
    }
  },
});
</script>

<template>
  <Drawer
    :title="drawerTitle"
    class="w-[720px]"
    :show-cancel-button="false"
    :show-confirm-button="false"
  >
    <Descriptions bordered :column="1" size="middle" :label-style="{ width: '150px' }">
      <DescriptionsItem label="平台类型">
        <Tag>{{ getSocialTypeLabel(detail?.type) }}</Tag>
      </DescriptionsItem>
      <DescriptionsItem label="OpenID">
        {{ detail?.openid }}
      </DescriptionsItem>
      <DescriptionsItem label="UnionID">
        {{ detail?.unionid || '-' }}
      </DescriptionsItem>
      <DescriptionsItem label="昵称">
        {{ detail?.nickname || '-' }}
      </DescriptionsItem>
      <DescriptionsItem label="头像">
        <Image v-if="detail?.avatar" :src="detail.avatar" :width="40" :height="40" />
        <span v-else>-</span>
      </DescriptionsItem>
      <DescriptionsItem label="绑定用户">
        {{ detail?.user_email || detail?.user_full_name || '-' }}
      </DescriptionsItem>
      <DescriptionsItem label="Token">
        {{ detail?.token || '-' }}
      </DescriptionsItem>
      <DescriptionsItem label="Token 原始信息">
        <pre class="max-h-40 overflow-auto whitespace-pre-wrap">{{ detail?.raw_token_info || '-' }}</pre>
      </DescriptionsItem>
      <DescriptionsItem label="用户原始信息">
        <pre class="max-h-40 overflow-auto whitespace-pre-wrap">{{ detail?.raw_user_info || '-' }}</pre>
      </DescriptionsItem>
      <DescriptionsItem label="授权 Code">
        {{ detail?.code || '-' }}
      </DescriptionsItem>
      <DescriptionsItem label="State">
        {{ detail?.state || '-' }}
      </DescriptionsItem>
    </Descriptions>
  </Drawer>
</template>
