<script lang="ts" setup>
import type {
  OnActionClickParams,
  VxeTableGridOptions,
} from '#/adapter/vxe-table';
import type { FileAssetRecord } from '#/api';

import { Page, useVbenModal } from '@vben/common-ui';
import { Plus } from '@vben/icons';

import { Button, message } from 'ant-design-vue';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  deleteFileApi,
  downloadApi,
  getFileDownloadUrl,
  listFilesApi,
} from '#/api';

import { buildKeyword } from '../system/shared/utils';
import { useColumns, useGridFormSchema } from './data';
import Upload from './modules/upload.vue';

const [UploadModal, uploadModalApi] = useVbenModal({
  connectedComponent: Upload,
  destroyOnClose: true,
});

function onActionClick({ code, row }: OnActionClickParams<FileAssetRecord>) {
  switch (code) {
    case 'delete': {
      void onDelete(row);
      break;
    }
    case 'download': {
      void onDownload(row);
      break;
    }
  }
}

async function onDownload(row: FileAssetRecord) {
  await downloadApi(getFileDownloadUrl(row.id), row.original_name);
}

async function onDelete(row: FileAssetRecord) {
  const hideLoading = message.loading({
    content: `正在删除 ${row.original_name}`,
    duration: 0,
    key: 'file_delete',
  });
  try {
    await deleteFileApi(row.id);
    message.success({
      content: `${row.original_name} 已删除`,
      key: 'file_delete',
    });
    onRefresh();
  } catch {
    hideLoading();
  }
}

const [Grid, gridApi] = useVbenVxeGrid({
  formOptions: {
    schema: useGridFormSchema(),
    submitOnChange: true,
  },
  gridOptions: {
    columns: useColumns(onActionClick),
    height: 'auto',
    keepSource: true,
    proxyConfig: {
      ajax: {
        query: async ({ page }, formValues) => {
          return await listFilesApi({
            keyword: buildKeyword(formValues.keyword) || undefined,
            page: page.currentPage,
            page_size: page.pageSize,
          });
        },
      },
    },
    rowConfig: {
      keyField: 'id',
    },
    toolbarConfig: {
      custom: true,
      export: false,
      refresh: true,
      search: true,
      zoom: true,
    },
  } as VxeTableGridOptions<FileAssetRecord>,
});

function onRefresh() {
  gridApi.query();
}

function onUpload() {
  uploadModalApi.open();
}
</script>

<template>
  <Page auto-content-height>
    <UploadModal @success="onRefresh" />
    <Grid table-title="文件列表">
      <template #toolbar-tools>
        <Button v-access:code="'system:file:upload'" type="primary" @click="onUpload">
          <Plus class="size-5" />
          上传文件
        </Button>
      </template>
    </Grid>
  </Page>
</template>
