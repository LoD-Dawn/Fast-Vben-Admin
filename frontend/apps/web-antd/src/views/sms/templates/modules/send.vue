<script lang="ts" setup>
import type { SmsTemplateRecord } from '#/api';

import { computed, ref } from 'vue';

import { useVbenDrawer } from '@vben/common-ui';

import { message } from 'ant-design-vue';

import { useVbenForm } from '#/adapter/form';
import { sendSmsTemplateTestApi } from '#/api';

import { useSendFormSchema } from '../data';

const template = ref<SmsTemplateRecord>();

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
      const smsLog = await sendSmsTemplateTestApi(template.value.id, {
        mobile: values.mobile,
        template_params: templateParams,
      });
      if (smsLog.send_status === 'success') {
        message.success('测试短信已由调试渠道记录');
      } else {
        message.warning(smsLog.api_send_message || '短信发送失败，详情请查看短信日志');
      }
      drawerApi.close();
    } catch {
      drawerApi.unlock();
    }
  },
  onOpenChange(isOpen) {
    if (!isOpen) return;

    template.value = drawerApi.getData<SmsTemplateRecord>();
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
  template.value ? `发送测试短信 - ${template.value.name}` : '发送测试短信',
);

function getTemplateParams(data?: SmsTemplateRecord) {
  return data?.params
    .split(',')
    .map((param) => param.trim())
    .filter(Boolean) ?? [];
}

function buildFormSchema(data?: SmsTemplateRecord) {
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
  <Drawer :title="drawerTitle" class="w-[560px]">
    <Form />
  </Drawer>
</template>
