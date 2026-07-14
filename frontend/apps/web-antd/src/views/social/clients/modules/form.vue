<script lang="ts" setup>
import type { SocialClientPayload, SocialClientRecord } from '#/api';

import { computed, ref } from 'vue';

import { useVbenDrawer } from '@vben/common-ui';

import { useVbenForm } from '#/adapter/form';
import {
  createSocialClientApi,
  getSocialClientApi,
  updateSocialClientApi,
} from '#/api';

import { useFormSchema } from '../data';

const emits = defineEmits<{ success: [] }>();

const clientId = ref<string>();

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
      agent_id: values.agent_id || undefined,
      client_id: values.client_id,
      client_secret:
        values.client_secret && values.client_secret !== '******'
          ? values.client_secret
          : undefined,
      ...(clientId.value && values.client_secret !== '******' && values.client_secret
        ? { current_password: values.current_password || undefined }
        : {}),
      is_active: values.is_active ?? true,
      name: values.name,
      remark: values.remark || undefined,
      social_type: values.social_type,
      user_type: values.user_type || 'admin',
    };

    drawerApi.lock();
    try {
      if (clientId.value) {
        await updateSocialClientApi(clientId.value, payload);
      } else {
        await createSocialClientApi(payload as SocialClientPayload);
      }
      emits('success');
      drawerApi.close();
    } catch {
      drawerApi.unlock();
    }
  },
  async onOpenChange(isOpen) {
    if (!isOpen) return;

    const data = drawerApi.getData<SocialClientRecord>();
    formApi.resetForm();
    clientId.value = data?.id;

    if (data?.id) {
      drawerApi.lock();
      try {
        await formApi.setValues(await getSocialClientApi(data.id));
      } finally {
        drawerApi.unlock();
      }
    }
  },
});

const drawerTitle = computed(() =>
  clientId.value ? '编辑三方登录客户端' : '新增三方登录客户端',
);
</script>

<template>
  <Drawer :title="drawerTitle" class="w-[640px]">
    <Form />
  </Drawer>
</template>
