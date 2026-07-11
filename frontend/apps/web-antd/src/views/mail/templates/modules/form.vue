<script lang="ts" setup>
import type { MailTemplatePayload, MailTemplateRecord } from '#/api';

import { computed, ref } from 'vue';

import { useVbenDrawer } from '@vben/common-ui';

import { useVbenForm } from '#/adapter/form';
import { createMailTemplateApi, updateMailTemplateApi } from '#/api';

import { useFormSchema } from '../data';

const emits = defineEmits<{ success: [] }>();

const templateId = ref<string>();

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
      account_id: values.account_id || undefined,
      code: values.code,
      content: values.content,
      is_active: values.is_active ?? true,
      name: values.name,
      nickname: values.nickname || undefined,
      remark: values.remark || undefined,
      title: values.title,
    };

    drawerApi.lock();
    try {
      if (templateId.value) {
        await updateMailTemplateApi(templateId.value, payload);
      } else {
        await createMailTemplateApi(payload as MailTemplatePayload);
      }
      emits('success');
      drawerApi.close();
    } catch {
      drawerApi.unlock();
    }
  },
  onOpenChange(isOpen) {
    if (!isOpen) return;

    const data = drawerApi.getData<MailTemplateRecord>();
    formApi.resetForm();
    templateId.value = data?.id;

    if (data) {
      formApi.setValues(data);
    }
  },
});

const drawerTitle = computed(() =>
  templateId.value ? '编辑邮件模板' : '新增邮件模板',
);
</script>

<template>
  <Drawer :title="drawerTitle" class="w-[760px]">
    <Form />
  </Drawer>
</template>
