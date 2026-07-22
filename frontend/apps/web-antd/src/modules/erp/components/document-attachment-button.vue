<script lang="ts" setup>
import { ref } from 'vue';

import { Button } from 'ant-design-vue';

import DocumentAttachments from '#/modules/erp/components/document-attachments.vue';

defineProps<{ documentId: string; documentType: string }>();

const open = ref(false);
</script>

<template>
  <DocumentAttachments v-model:open="open" :document-id="documentId" :document-type="documentType" />
  <Button v-access:code="'erp:attachment:list'" size="small" type="link" @click="open = true">
    附件
  </Button>
</template>
