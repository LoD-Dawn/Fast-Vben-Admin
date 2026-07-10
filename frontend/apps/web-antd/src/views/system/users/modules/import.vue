<script lang="ts" setup>
import type { UploadProps } from 'ant-design-vue';

import { ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';

import { message, UploadDragger } from 'ant-design-vue';

import { importUsersApi } from '#/api';
import { $t } from '#/locales';

const emits = defineEmits<{ success: [] }>();

const importing = ref(false);

const [Modal, modalApi] = useVbenModal({
  footer: false,
});

const beforeUpload: UploadProps['beforeUpload'] = async (file) => {
  importing.value = true;
  modalApi.lock();
  try {
    const result = await importUsersApi(file);
    if (result.failed > 0) {
      message.warning(
        $t('system.user.importResult', [result.success, result.failed]),
      );
    } else {
      message.success($t('system.user.importSuccess', [result.success]));
    }
    modalApi.close();
    emits('success');
  } catch {
    modalApi.unlock();
  } finally {
    importing.value = false;
    modalApi.lock(false);
  }
  return false;
};
</script>

<template>
  <Modal :title="$t('system.user.importTitle')">
    <div class="px-1 pb-6">
      <UploadDragger
        :before-upload="beforeUpload"
        :disabled="importing"
        :max-count="1"
        :show-upload-list="false"
        accept=".csv"
      >
        <div class="flex flex-col items-center py-8">
          <IconifyIcon
            class="mb-3 size-12 text-muted-foreground"
            icon="lucide:cloud-upload"
          />
          <p class="text-base">{{ $t('system.user.importHint') }}</p>
          <p class="mt-1 text-sm text-muted-foreground">
            {{ $t('system.user.importFileType') }}
          </p>
        </div>
      </UploadDragger>
    </div>
  </Modal>
</template>
