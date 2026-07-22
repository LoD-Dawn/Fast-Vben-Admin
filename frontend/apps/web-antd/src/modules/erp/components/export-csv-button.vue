<script lang="ts" setup>
import type { ErpExportResource } from '#/modules/erp/api/erp';

import { Download } from '@vben/icons';
import { Button } from 'ant-design-vue';

import { downloadApi } from '#/api';
import { erpExportPaths } from '#/modules/erp/api/erp';

const props = defineProps<{
  fileName: string;
  permission: string;
  query?: Record<string, string | undefined>;
  resource: ErpExportResource;
}>();

async function download() {
  const query = new URLSearchParams(
    Object.entries(props.query ?? {}).filter(
      (entry): entry is [string, string] => entry[1] !== undefined,
    ),
  ).toString();
  const path = `${erpExportPaths[props.resource]}${query ? `?${query}` : ''}`;
  await downloadApi(path, props.fileName);
}
</script>

<template>
  <Button
    v-access:code="permission"
    class="gap-1"
    title="导出当前列表"
    @click="download"
  >
    <Download class="size-4" />
    导出
  </Button>
</template>
