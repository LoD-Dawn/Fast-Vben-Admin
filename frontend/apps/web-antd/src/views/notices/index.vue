<script lang="ts" setup>
import type {
  OnActionClickParams,
  VxeTableGridOptions,
} from '#/adapter/vxe-table';
import type { NoticeRecord } from '#/api';

import { Page, useVbenDrawer } from '@vben/common-ui';
import { Plus } from '@vben/icons';

import { Button, message } from 'ant-design-vue';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  deleteNoticeApi,
  listNoticesApi,
  publishNoticeApi,
  withdrawNoticeApi,
} from '#/api';

import { buildKeyword, confirmAction } from '../system/shared/utils';
import { useColumns, useGridFormSchema } from './data';
import Form from './modules/form.vue';

const [FormDrawer, formDrawerApi] = useVbenDrawer({
  connectedComponent: Form,
  destroyOnClose: true,
});

function onActionClick({ code, row }: OnActionClickParams<NoticeRecord>) {
  switch (code) {
    case 'delete': {
      void onDelete(row);
      break;
    }
    case 'edit': {
      formDrawerApi.setData(row).open();
      break;
    }
    case 'publish': {
      void onPublish(row);
      break;
    }
    case 'withdraw': {
      void onWithdraw(row);
      break;
    }
  }
}

async function onPublish(row: NoticeRecord) {
  try {
    await confirmAction(`确认发布公告【${row.title}】吗？`, '发布公告');
    await publishNoticeApi(row.id);
    message.success('公告已发布');
    onRefresh();
  } catch {
    // cancelled
  }
}

async function onWithdraw(row: NoticeRecord) {
  try {
    await confirmAction(`确认撤回公告【${row.title}】吗？`, '撤回公告');
    await withdrawNoticeApi(row.id);
    message.success('公告已撤回');
    onRefresh();
  } catch {
    // cancelled
  }
}

async function onDelete(row: NoticeRecord) {
  const hideLoading = message.loading({
    content: `正在删除 ${row.title}`,
    duration: 0,
    key: 'notice_delete',
  });
  try {
    await deleteNoticeApi(row.id);
    message.success({
      content: `${row.title} 已删除`,
      key: 'notice_delete',
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
          return await listNoticesApi({
            keyword: buildKeyword(formValues.keyword) || undefined,
            page: page.currentPage,
            page_size: page.pageSize,
            status: formValues.status || undefined,
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
  } as VxeTableGridOptions<NoticeRecord>,
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
    <Grid table-title="公告列表">
      <template #toolbar-tools>
        <Button type="primary" @click="onCreate">
          <Plus class="size-5" />
          新增公告
        </Button>
      </template>
    </Grid>
  </Page>
</template>
