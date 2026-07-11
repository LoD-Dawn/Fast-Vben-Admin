<script lang="ts" setup>
import type { MailAccountPayload, MailAccountRecord } from '#/api';

import { computed, ref } from 'vue';

import { useVbenDrawer } from '@vben/common-ui';

import { useVbenForm } from '#/adapter/form';
import { createMailAccountApi, updateMailAccountApi } from '#/api';

import { useFormSchema } from '../data';

const emits = defineEmits<{ success: [] }>();

const accountId = ref<string>();

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
      code: values.code,
      email: values.email,
      host: values.host,
      is_active: values.is_active ?? true,
      is_default: values.is_default ?? false,
      name: values.name,
      password:
        values.password && values.password !== '******'
          ? values.password
          : undefined,
      port: values.port || 465,
      remark: values.remark || undefined,
      ssl_enable: values.ssl_enable ?? true,
      starttls_enable: values.starttls_enable ?? false,
      username: values.username || undefined,
    };

    drawerApi.lock();
    try {
      if (accountId.value) {
        await updateMailAccountApi(accountId.value, payload);
      } else {
        await createMailAccountApi(payload as MailAccountPayload);
      }
      emits('success');
      drawerApi.close();
    } catch {
      drawerApi.unlock();
    }
  },
  onOpenChange(isOpen) {
    if (!isOpen) return;

    const data = drawerApi.getData<MailAccountRecord>();
    formApi.resetForm();
    accountId.value = data?.id;

    if (data) {
      formApi.setValues(data);
    }
  },
});

const drawerTitle = computed(() =>
  accountId.value ? '编辑邮箱账号' : '新增邮箱账号',
);
</script>

<template>
  <Drawer :title="drawerTitle" class="w-[680px]">
    <Form />
  </Drawer>
</template>
