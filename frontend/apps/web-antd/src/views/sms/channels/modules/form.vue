<script lang="ts" setup>
import type {
  SmsChannelPayload,
  SmsChannelRecord,
} from '#/api';

import { computed, ref } from 'vue';

import { useVbenDrawer } from '@vben/common-ui';

import { useVbenForm } from '#/adapter/form';
import { createSmsChannelApi, updateSmsChannelApi } from '#/api';

import { useFormSchema } from '../data';

const emits = defineEmits<{ success: [] }>();

const channelId = ref<string>();

const [Form, formApi] = useVbenForm({
  schema: useFormSchema(),
  showDefaultActions: false,
});

const [Drawer, drawerApi] = useVbenDrawer({
  async onConfirm() {
    const { valid } = await formApi.validate();
    if (!valid) return;

    const values = await formApi.getValues();
    const payload = {
      api_key: values.api_key || undefined,
      api_secret:
        values.api_secret && values.api_secret !== '******'
          ? values.api_secret
          : undefined,
      callback_url: values.callback_url || undefined,
      code: values.code,
      is_active: values.is_active ?? true,
      is_default: values.is_default ?? false,
      name: values.name,
      provider: values.provider || 'debug',
      remark: values.remark || undefined,
      signature: values.signature,
    };

    drawerApi.lock();
    try {
      if (channelId.value) {
        await updateSmsChannelApi(channelId.value, payload);
      } else {
        await createSmsChannelApi(payload as SmsChannelPayload);
      }
      emits('success');
      drawerApi.close();
    } catch {
      drawerApi.unlock();
    }
  },
  onOpenChange(isOpen) {
    if (!isOpen) return;

    const data = drawerApi.getData<SmsChannelRecord>();
    formApi.resetForm();
    channelId.value = data?.id;

    if (data) {
      formApi.setValues(data);
    }
  },
});

const drawerTitle = computed(() =>
  channelId.value ? '编辑短信渠道' : '新增短信渠道',
);
</script>

<template>
  <Drawer :title="drawerTitle" class="w-[680px]">
    <Form />
  </Drawer>
</template>
