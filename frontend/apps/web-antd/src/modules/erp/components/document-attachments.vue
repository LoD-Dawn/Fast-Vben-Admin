<script lang="ts" setup>
import type { DocumentAttachmentRecord } from '#/modules/erp/api/erp';

import { ref, watch } from 'vue';

import { IconifyIcon } from '@vben/icons';
import { Button, Drawer, Empty, Popconfirm, Spin, Tag } from 'ant-design-vue';

import {
  downloadApi,
  getFileDownloadUrl,
  uploadFileApi,
} from '#/api';
import {
  createDocumentAttachmentApi,
  deleteDocumentAttachmentApi,
  listDocumentAttachmentsApi,
} from '#/modules/erp/api/erp';

const props = withDefaults(
  defineProps<{
    documentId?: string;
    documentType?: string;
    open: boolean;
    readonly?: boolean;
  }>(),
  { readonly: false },
);

const emits = defineEmits<{ 'update:open': [value: boolean] }>();

const attachments = ref<DocumentAttachmentRecord[]>([]);
const inputRef = ref<HTMLInputElement>();
const loading = ref(false);
const uploading = ref(false);

async function load() {
  if (!props.documentId || !props.documentType) return;
  loading.value = true;
  try {
    attachments.value = (await listDocumentAttachmentsApi(props.documentType, props.documentId)).items;
  } finally {
    loading.value = false;
  }
}

watch(
  () => props.open,
  (open) => {
    if (open) void load();
  },
);

function chooseFile() {
  inputRef.value?.click();
}

async function upload(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (!file || !props.documentId || !props.documentType) return;
  uploading.value = true;
  try {
    const stored = await uploadFileApi(file);
    await createDocumentAttachmentApi(
      props.documentType,
      props.documentId,
      stored.id,
      attachments.value.length,
    );
    await load();
  } finally {
    uploading.value = false;
    if (inputRef.value) inputRef.value.value = '';
  }
}

async function remove(attachment: DocumentAttachmentRecord) {
  if (!props.documentId || !props.documentType) return;
  await deleteDocumentAttachmentApi(props.documentType, props.documentId, attachment.id);
  await load();
}

async function download(attachment: DocumentAttachmentRecord) {
  await downloadApi(
    getFileDownloadUrl(attachment.file_id),
    attachment.file_name,
  );
}
</script>

<template>
  <Drawer
    :open="open"
    placement="right"
    title="单据附件"
    width="min(560px, 100vw)"
    @close="emits('update:open', false)"
  >
    <input ref="inputRef" class="hidden" type="file" @change="upload" />
    <div class="mb-5 flex items-center justify-between border-b border-[var(--vben-border-color)] pb-4">
      <div class="text-sm text-[var(--vben-text-color-2)]">附件随单据留档，不随单据状态变化而丢失。</div>
      <Button v-if="!readonly" v-access:code="'erp:attachment:create'" :loading="uploading" type="primary" @click="chooseFile">
        <IconifyIcon class="size-4" icon="lucide:upload" />上传
      </Button>
    </div>
    <Spin :spinning="loading">
      <Empty v-if="!attachments.length" description="暂无附件" />
      <div v-else class="space-y-2">
        <div v-for="attachment in attachments" :key="attachment.id" class="flex items-center gap-3 border-b border-[var(--vben-border-color)] py-3 last:border-b-0">
          <IconifyIcon class="size-5 shrink-0 text-[var(--vben-text-color-2)]" icon="lucide:paperclip" />
          <div class="min-w-0 flex-1">
            <div class="truncate text-sm font-medium">{{ attachment.file_name }}</div>
            <div class="mt-1 flex gap-2 text-xs text-[var(--vben-text-color-2)]"><Tag>{{ attachment.content_type || '文件' }}</Tag><span>{{ attachment.size }} bytes</span></div>
          </div>
          <div class="flex items-center gap-1">
            <Button size="small" type="link" @click="download(attachment)">下载</Button>
            <Popconfirm v-if="!readonly" title="解除该附件与单据的关联？" @confirm="remove(attachment)">
              <Button v-access:code="'erp:attachment:delete'" danger size="small" type="link">移除</Button>
            </Popconfirm>
          </div>
        </div>
      </div>
    </Spin>
  </Drawer>
</template>
