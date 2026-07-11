<script lang="ts" setup>
import type {
  OnActionClickParams,
  VxeTableGridOptions,
} from '#/adapter/vxe-table';
import type { FileStorageChannelRecord } from '#/api';

import { Page, useVbenDrawer } from '@vben/common-ui';
import { Plus } from '@vben/icons';

import { Button, message } from 'ant-design-vue';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  deleteFileStorageChannelApi,
  listFileStorageChannelsApi,
  testFileStorageChannelApi,
  updateFileStorageChannelApi,
} from '#/api';

import { buildKeyword, confirmAction } from '../../system/shared/utils';
import { useColumns, useGridFormSchema } from './data';
import Form from './modules/form.vue';

const [FormDrawer, formDrawerApi] = useVbenDrawer({
  connectedComponent: Form,
  destroyOnClose: true,
});

async function onStatusChange(
  newStatus: boolean,
  row: FileStorageChannelRecord,
) {
  try {
    await confirmAction(
      `确认将存储渠道 ${row.name} 的状态切换为【${newStatus ? '启用' : '禁用'}】吗？`,
      '切换状态',
    );
    await updateFileStorageChannelApi(row.id, { is_active: newStatus });
    return true;
  } catch {
    return false;
  }
}

function onActionClick({ code, row }: OnActionClickParams<FileStorageChannelRecord>) {
  switch (code) {
    case 'delete': {
      void onDelete(row);
      break;
    }
    case 'edit': {
      formDrawerApi.setData(row).open();
      break;
    }
    case 'test': {
      void onTest(row);
      break;
    }
  }
}

async function onDelete(row: FileStorageChannelRecord) {
  try {
    await confirmAction(`确认删除存储渠道 ${row.name} 吗？`, '删除存储渠道');
    await deleteFileStorageChannelApi(row.id);
    message.success('存储渠道已删除');
    onRefresh();
  } catch {
    // 用户取消或接口失败时由全局错误处理接管
  }
}

async function onTest(row: FileStorageChannelRecord) {
  const hide = message.loading({
    content: `正在测试 ${row.name}`,
    duration: 0,
    key: 'file_channel_test',
  });
  try {
    await testFileStorageChannelApi(row.id);
    message.success({
      content: `${row.name} 连接可用`,
      key: 'file_channel_test',
    });
  } catch {
    hide();
  }
}

const [Grid, gridApi] = useVbenVxeGrid({
  formOptions: {
    schema: useGridFormSchema(),
    submitOnChange: true,
  },
  gridOptions: {
    columns: useColumns(onActionClick, onStatusChange),
    height: 'auto',
    keepSource: true,
    proxyConfig: {
      ajax: {
        query: async ({ page }, formValues) => {
          return await listFileStorageChannelsApi({
            is_active: formValues.is_active,
            keyword: buildKeyword(formValues.keyword),
            page: page.currentPage,
            page_size: page.pageSize,
            provider: formValues.provider || undefined,
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
  } as VxeTableGridOptions<FileStorageChannelRecord>,
});

function onRefresh() {
  gridApi.query();
}

function onCreate() {
  formDrawerApi.setData(undefined).open();
}
</script>

<template>
  <Page auto-content-height>
    <FormDrawer @success="onRefresh" />
    <Grid table-title="存储渠道">
      <template #toolbar-tools>
        <Button
          v-access:code="'system:file:channel:create'"
          type="primary"
          @click="onCreate"
        >
          <Plus class="size-5" />
          新增渠道
        </Button>
      </template>
    </Grid>
  </Page>
</template>
