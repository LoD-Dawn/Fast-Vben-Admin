<script lang="ts" setup>
import { ref, watch } from 'vue';

import { Input, Modal } from 'ant-design-vue';

const props = defineProps<{
  impact: string;
  onConfirm: (reason: string) => Promise<void> | void;
  open: boolean;
  title: string;
}>();

const emits = defineEmits<{ 'update:open': [value: boolean] }>();

const reason = ref('');
const submitting = ref(false);

watch(
  () => props.open,
  (open) => {
    if (open) reason.value = '';
  },
);

async function confirm() {
  const trimmedReason = reason.value.trim();
  if (!trimmedReason || submitting.value) return;

  submitting.value = true;
  try {
    await props.onConfirm(trimmedReason);
    emits('update:open', false);
  } finally {
    submitting.value = false;
  }
}

function cancel() {
  if (!submitting.value) emits('update:open', false);
}
</script>

<template>
  <Modal
    :cancel-button-props="{ disabled: submitting }"
    :confirm-loading="submitting"
    :mask-closable="!submitting"
    :ok-button-props="{ disabled: !reason.trim() }"
    :open="open"
    :title="title"
    ok-text="确认反审核"
    @cancel="cancel"
    @ok="confirm"
  >
    <div class="rounded border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:border-amber-500/40 dark:bg-amber-500/10 dark:text-amber-100">
      {{ impact }}
    </div>
    <div class="mt-4">
      <label class="mb-1.5 block text-sm font-medium" for="erp-reverse-reason">
        反审核原因
      </label>
      <Input.TextArea
        id="erp-reverse-reason"
        v-model:value="reason"
        :auto-size="{ minRows: 3, maxRows: 6 }"
        :disabled="submitting"
        :maxlength="500"
        placeholder="请说明反审核原因"
        show-count
      />
    </div>
  </Modal>
</template>
