<script lang="ts" setup>
import type { MailTemplateRecord } from '#/api';

import { computed, ref } from 'vue';

import { useVbenDrawer } from '@vben/common-ui';

import { message } from 'ant-design-vue';

import { useVbenForm } from '#/adapter/form';
import { sendMailTemplateTestApi } from '#/api';

import { useSendFormSchema } from '../data';

const template = ref<MailTemplateRecord>();

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
      const mailLog = await sendMailTemplateTestApi(template.value.id, {
        template_params: templateParams,
        to_email: values.to_email,
      });
      if (mailLog.send_status === 'success') {
        message.success('测试邮件已发送，请查看收件箱');
      } else {
        message.warning(mailLog.send_message || '邮件发送失败，详情请查看邮件日志');
      }
      drawerApi.close();
    } catch {
      drawerApi.unlock();
    }
  },
  onOpenChange(isOpen) {
    if (!isOpen) return;

    template.value = drawerApi.getData<MailTemplateRecord>();
    formApi.resetForm();
    formApi.setState({
      schema: buildFormSchema(template.value),
    });
    if (template.value) {
      formApi.setValues({
        content: template.value.content,
        title: template.value.title,
      });
    }
  },
});

const drawerTitle = computed(() =>
  template.value ? `发送测试邮件 - ${template.value.name}` : '发送测试邮件',
);

function getTemplateParams(data?: MailTemplateRecord) {
  return data?.params
    .split(',')
    .map((param) => param.trim())
    .filter(Boolean) ?? [];
}

function buildFormSchema(data?: MailTemplateRecord) {
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
  <Drawer :title="drawerTitle" class="w-[640px]">
    <Form />
  </Drawer>
</template>
