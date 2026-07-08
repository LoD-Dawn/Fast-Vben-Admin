<script lang="ts" setup>
import type {
  OnActionClickParams,
  VxeTableGridOptions,
} from '#/adapter/vxe-table';
import type { UserMessageRecord } from '#/api';

import { Page, useVbenModal } from '@vben/common-ui';

import { message } from 'ant-design-vue';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { listMyMessagesApi, markMessageReadApi } from '#/api';

import { useColumns, useGridFormSchema } from './data';
import Detail from './modules/detail.vue';

const [DetailModal, detailModalApi] = useVbenModal({
  connectedComponent: Detail,
  destroyOnClose: true,
});

function onActionClick({ code, row }: OnActionClickParams<UserMessageRecord>) {
  switch (code) {
    case 'detail': {
      void onDetail(row);
      break;
    }
    case 'read': {
      void onMarkRead(row);
      break;
    }
  }
}

async function onDetail(row: UserMessageRecord) {
  if (!row.is_read) {
    try {
      const updated = await markMessageReadApi(row.id);
      Object.assign(row, updated);
      detailModalApi.setData(updated).open();
      onRefresh();
      return;
    } catch {
      detailModalApi.setData(row).open();
      return;
    }
  }
  detailModalApi.setData(row).open();
}

async function onMarkRead(row: UserMessageRecord) {
  const hideLoading = message.loading({
    content: `正在标记 ${row.title}`,
    duration: 0,
    key: 'message_read',
  });
  try {
    await markMessageReadApi(row.id);
    message.success({
      content: '消息已标记为已读',
      key: 'message_read',
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
          return await listMyMessagesApi({
            is_read:
              formValues.is_read === undefined || formValues.is_read === null
                ? undefined
                : formValues.is_read,
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
  } as VxeTableGridOptions<UserMessageRecord>,
});

function onRefresh() {
  gridApi.query();
}
</script>

<template>
  <Page auto-content-height>
    <DetailModal />
    <Grid table-title="消息列表" />
  </Page>
</template>
