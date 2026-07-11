<script lang="ts" setup>
import type { UploadProps } from 'ant-design-vue';

import { ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';

import { Checkbox, message, UploadDragger } from 'ant-design-vue';

import { getUploadConfigApi, uploadFileApi } from '#/api';

const emits = defineEmits<{ success: [] }>();

const uploading = ref(false);
const uploadPublic = ref(false);

const [Modal, modalApi] = useVbenModal({
  footer: false,
  async onOpenChange(isOpen) {
    if (isOpen) {
      const config = await getUploadConfigApi();
      uploadPublic.value = config.default_public;
    }
  },
});

const beforeUpload: UploadProps['beforeUpload'] = async (file) => {
  uploading.value = true;
  modalApi.lock();
  try {
    await uploadFileApi(file, uploadPublic.value);
    message.success('文件已上传');
    modalApi.close();
    emits('success');
  } catch {
    modalApi.unlock();
  } finally {
    uploading.value = false;
    modalApi.lock(false);
  }
  return false;
};
</script>

<template>
  <Modal title="上传文件">
    <div class="px-1 pb-6">
      <UploadDragger
        :before-upload="beforeUpload"
        :disabled="uploading"
        :max-count="1"
        :show-upload-list="false"
      >
        <div class="flex flex-col items-center py-8">
          <IconifyIcon
            class="mb-3 size-12 text-muted-foreground"
            icon="lucide:cloud-upload"
          />
          <p class="text-base">点击或拖拽文件到此处上传</p>
          <p class="mt-1 text-sm text-muted-foreground">
            支持单个文件上传
          </p>
        </div>
      </UploadDragger>
      <div class="mt-6">
        <Checkbox v-model:checked="uploadPublic">公开访问</Checkbox>
      </div>
    </div>
  </Modal>
</template>
