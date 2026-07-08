<script lang="ts" setup>
import type { UserMessageRecord } from '#/api';

import { ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';

import { Descriptions, DescriptionsItem, Tag } from 'ant-design-vue';

const messageData = ref<UserMessageRecord>();

const [Modal, modalApi] = useVbenModal({
  footer: false,
  onOpenChange(isOpen) {
    if (isOpen) {
      messageData.value = modalApi.getData<UserMessageRecord>();
    }
  },
});
</script>

<template>
  <Modal title="消息详情" class="w-[680px]">
    <Descriptions
      v-if="messageData"
      bordered
      class="mx-4 pb-6"
      :column="1"
      size="small"
    >
      <DescriptionsItem label="标题">
        {{ messageData.title }}
      </DescriptionsItem>
      <DescriptionsItem label="类型">
        {{ messageData.type || '-' }}
      </DescriptionsItem>
      <DescriptionsItem label="状态">
        <Tag :color="messageData.is_read ? 'default' : 'processing'">
          {{ messageData.is_read ? '已读' : '未读' }}
        </Tag>
      </DescriptionsItem>
      <DescriptionsItem label="内容">
        <div class="whitespace-pre-wrap break-words">
          {{ messageData.content }}
        </div>
      </DescriptionsItem>
      <DescriptionsItem label="创建时间">
        {{ messageData.created_at || '-' }}
      </DescriptionsItem>
      <DescriptionsItem label="阅读时间">
        {{ messageData.read_at || '-' }}
      </DescriptionsItem>
    </Descriptions>
  </Modal>
</template>
