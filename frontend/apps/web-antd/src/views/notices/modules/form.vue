<script lang="ts" setup>
import type { NoticePayload, NoticeRecord, NoticeUpdatePayload } from '#/api';

import { computed, ref } from 'vue';

import { useVbenDrawer } from '@vben/common-ui';

import {
  createNoticeApi,
  updateNoticeApi,
} from '#/api';

import { useVbenForm } from '#/adapter/form';

import { useFormSchema } from '../data';

const emits = defineEmits<{ success: [] }>();

const noticeId = ref<string>();

const [Form, formApi] = useVbenForm({
  schema: useFormSchema(),
  showDefaultActions: false,
});

const [Drawer, drawerApi] = useVbenDrawer({
  async onConfirm() {
    const { valid } = await formApi.validate();
    if (!valid) return;

    const values = await formApi.getValues();
    drawerApi.lock();
    try {
      if (noticeId.value) {
        await updateNoticeApi(
          noticeId.value,
          values as NoticeUpdatePayload,
        );
      } else {
        await createNoticeApi(values as NoticePayload);
      }
      emits('success');
      drawerApi.close();
    } catch {
      drawerApi.unlock();
    }
  },
  onOpenChange(isOpen) {
    if (!isOpen) return;

    const data = drawerApi.getData<NoticeRecord>();
    formApi.resetForm();
    noticeId.value = data?.id;

    if (data) {
      formApi.setValues(data);
    }
  },
});

const drawerTitle = computed(() =>
  noticeId.value ? '编辑公告' : '新增公告',
);
</script>

<template>
  <Drawer :title="drawerTitle" class="w-[720px]">
    <Form />
  </Drawer>
</template>
