<script lang="ts" setup>
import type { SiteMessageTemplateRecord } from '#/api';

import { computed, ref } from 'vue';

import { useVbenDrawer } from '@vben/common-ui';

import { message } from 'ant-design-vue';

import { useVbenForm } from '#/adapter/form';
import { sendSiteMessageTemplateTestApi } from '#/api';

import { useSendFormSchema } from '../data';

const emits = defineEmits<{ success: [] }>();

const template = ref<SiteMessageTemplateRecord>();

const [Form, formApi] = useVbenForm({
  showDefaultActions: false,
});

const [Drawer, drawerApi] = useVbenDrawer({
  async onConfirm() {
    const { valid } = await formApi.validate();
    if (!valid || !template.value) return;

    const values = await formApi.getValues();
    const templateParams = Object.fromEntries(
      getTemplateParams(template.value).map((param) => [
        param,
        String(values[`param_${param}`] || ''),
      ]),
    );

    drawerApi.lock();
    try {
      await sendSiteMessageTemplateTestApi(template.value.id, {
        template_params: templateParams,
        user_id: values.user_id,
      });
      message.success('测试站内信已发送');
      emits('success');
      drawerApi.close();
    } catch {
      drawerApi.unlock();
    }
  },
  onOpenChange(isOpen) {
    if (!isOpen) return;

    template.value = drawerApi.getData<SiteMessageTemplateRecord>();
    formApi.resetForm();
    formApi.setState({
      schema: buildFormSchema(template.value),
    });
    if (template.value) {
      formApi.setValues({ content: template.value.content });
    }
  },
});

const drawerTitle = computed(() =>
  template.value ? `发送测试站内信 - ${template.value.name}` : '发送测试站内信',
);

function getTemplateParams(data?: SiteMessageTemplateRecord) {
  return data?.params
    .split(',')
    .map((param) => param.trim())
    .filter(Boolean) ?? [];
}

function buildFormSchema(data?: SiteMessageTemplateRecord) {
  const schema = useSendFormSchema();
  for (const param of getTemplateParams(data)) {
    schema.push({
      component: 'Input',
      componentProps: {
        placeholder: `请输入参数 ${param}`,
      },
      fieldName: `param_${param}`,
      label: `参数 ${param}`,
      rules: 'required',
    });
  }
  return schema;
}
</script>

<template>
  <Drawer :title="drawerTitle" class="w-[600px]">
    <Form />
  </Drawer>
</template>
