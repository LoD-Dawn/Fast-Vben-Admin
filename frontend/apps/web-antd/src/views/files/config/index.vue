<script lang="ts" setup>
import { onMounted } from 'vue';

import { Page } from '@vben/common-ui';

import { Button, message } from 'ant-design-vue';

import { useVbenForm } from '#/adapter/form';
import { getUploadConfigApi, updateUploadConfigApi } from '#/api';

import { useFormSchema } from './data';

const [Form, formApi] = useVbenForm({
  commonConfig: {
    componentProps: {
      class: 'max-w-[720px]',
    },
  },
  schema: useFormSchema(),
  showDefaultActions: false,
});

async function loadConfig() {
  const config = await getUploadConfigApi();
  formApi.setValues(config);
}

async function onSave() {
  const { valid } = await formApi.validate();
  if (!valid) return;

  const values = await formApi.getValues();
  await updateUploadConfigApi({
    allowed_extensions: values.allowed_extensions,
    default_public: values.default_public ?? false,
    max_size_mb: values.max_size_mb,
    presigned_url_expire_seconds: values.presigned_url_expire_seconds,
  });
  message.success('上传配置已保存');
  await loadConfig();
}

onMounted(loadConfig);
</script>

<template>
  <Page auto-content-height title="上传配置">
    <div class="max-w-[760px]">
      <Form />
      <div class="mt-4 pl-[120px]">
        <Button
          v-access:code="'system:file:config:update'"
          type="primary"
          @click="onSave"
        >
          保存配置
        </Button>
      </div>
    </div>
  </Page>
</template>
