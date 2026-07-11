<script lang="ts" setup>
import type {
  SmsTemplatePayload,
  SmsTemplateRecord,
} from '#/api';

import { computed, ref } from 'vue';

import { useVbenDrawer } from '@vben/common-ui';

import { useVbenForm } from '#/adapter/form';
import { createSmsTemplateApi, updateSmsTemplateApi } from '#/api';

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
      api_template_id: values.api_template_id || undefined,
      channel_id: values.channel_id || undefined,
      code: values.code,
      content: values.content,
      is_active: values.is_active ?? true,
      name: values.name,
      remark: values.remark || undefined,
      type: values.type || 'notification',
    };

    drawerApi.lock();
    try {
      if (templateId.value) {
        await updateSmsTemplateApi(templateId.value, payload);
      } else {
        await createSmsTemplateApi(payload as SmsTemplatePayload);
      }
      emits('success');
      drawerApi.close();
    } catch {
      drawerApi.unlock();
    }
  },
  onOpenChange(isOpen) {
    if (!isOpen) return;

    const data = drawerApi.getData<SmsTemplateRecord>();
    formApi.resetForm();
    templateId.value = data?.id;

    if (data) {
      formApi.setValues(data);
    }
  },
});

const drawerTitle = computed(() =>
  templateId.value ? '编辑短信模板' : '新增短信模板',
);
</script>

<template>
  <Drawer :title="drawerTitle" class="w-[720px]">
    <Form />
  </Drawer>
</template>
