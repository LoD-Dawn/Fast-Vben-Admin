<script lang="ts" setup>
import type {
  SiteMessageTemplatePayload,
  SiteMessageTemplateRecord,
} from '#/api';

import { computed, ref } from 'vue';

import { useVbenDrawer } from '@vben/common-ui';

import { useVbenForm } from '#/adapter/form';
import {
  createSiteMessageTemplateApi,
  updateSiteMessageTemplateApi,
} from '#/api';

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
      code: values.code,
      content: values.content,
      is_active: values.is_active ?? true,
      name: values.name,
      remark: values.remark || undefined,
      sender_name: values.sender_name || '系统通知',
      type: values.type || 'system',
    };

    drawerApi.lock();
    try {
      if (templateId.value) {
        await updateSiteMessageTemplateApi(templateId.value, payload);
      } else {
        await createSiteMessageTemplateApi(
          payload as SiteMessageTemplatePayload,
        );
      }
      emits('success');
      drawerApi.close();
    } catch {
      drawerApi.unlock();
    }
  },
  onOpenChange(isOpen) {
    if (!isOpen) return;

    const data = drawerApi.getData<SiteMessageTemplateRecord>();
    formApi.resetForm();
    templateId.value = data?.id;

    if (data) {
      formApi.setValues(data);
    }
  },
});

const drawerTitle = computed(() =>
  templateId.value ? '编辑站内信模板' : '新增站内信模板',
);
</script>

<template>
  <Drawer :title="drawerTitle" class="w-[720px]">
    <Form />
  </Drawer>
</template>
