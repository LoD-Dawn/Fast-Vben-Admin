<script lang="ts" setup>
import type { SiteMessageRecord } from '#/api';

import { computed, ref } from 'vue';

import { useVbenDrawer } from '@vben/common-ui';
import { formatDateTime } from '@vben/utils';

import { Descriptions, Tag } from 'ant-design-vue';

const siteMessage = ref<SiteMessageRecord>();

const [Drawer, drawerApi] = useVbenDrawer({
  onOpenChange(isOpen) {
    siteMessage.value = isOpen
      ? drawerApi.getData<SiteMessageRecord>()
      : undefined;
  },
});

const templateParams = computed(() => siteMessage.value?.template_params || '-');
</script>

<template>
  <Drawer
    :show-cancel-button="false"
    :show-confirm-button="false"
    class="w-[760px]"
    title="站内信详情"
  >
    <Descriptions bordered :column="2" size="small">
      <Descriptions.Item label="接收用户">
        {{ siteMessage?.user_full_name || siteMessage?.user_email || '-' }}
      </Descriptions.Item>
      <Descriptions.Item label="用户邮箱">
        {{ siteMessage?.user_email || '-' }}
      </Descriptions.Item>
      <Descriptions.Item label="模板编码">
        {{ siteMessage?.template_code || '-' }}
      </Descriptions.Item>
      <Descriptions.Item label="发送人名称">
        {{ siteMessage?.sender_name || '-' }}
      </Descriptions.Item>
      <Descriptions.Item label="标题">
        {{ siteMessage?.title }}
      </Descriptions.Item>
      <Descriptions.Item label="模板类型">
        {{ siteMessage?.type || '-' }}
      </Descriptions.Item>
      <Descriptions.Item label="内容" :span="2">
        <div class="max-h-72 overflow-auto whitespace-pre-wrap break-words">
          {{ siteMessage?.content }}
        </div>
      </Descriptions.Item>
      <Descriptions.Item label="模板参数" :span="2">
        {{ templateParams }}
      </Descriptions.Item>
      <Descriptions.Item label="阅读状态">
        <Tag :color="siteMessage?.is_read ? 'default' : 'processing'">
          {{ siteMessage?.is_read ? '已读' : '未读' }}
        </Tag>
      </Descriptions.Item>
      <Descriptions.Item label="阅读时间">
        {{ formatDateTime(siteMessage?.read_at || '') }}
      </Descriptions.Item>
      <Descriptions.Item label="创建时间">
        {{ formatDateTime(siteMessage?.created_at || '') }}
      </Descriptions.Item>
    </Descriptions>
  </Drawer>
</template>
