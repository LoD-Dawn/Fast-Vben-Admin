<script lang="ts" setup>
import type {
  OnActionClickParams,
  VxeTableGridOptions,
} from '#/adapter/vxe-table';
import type { UserSessionRecord } from '#/api';

import { Page } from '@vben/common-ui';

import { message } from 'ant-design-vue';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { listUserSessionsApi, revokeUserSessionApi } from '#/api';
import { $t } from '#/locales';

import { buildKeyword, confirmAction } from '../shared/utils';
import { useColumns, useGridFormSchema } from './data';

function onActionClick({ code, row }: OnActionClickParams<UserSessionRecord>) {
  if (code === 'revoke') {
    void onRevoke(row);
  }
}

async function onRevoke(row: UserSessionRecord) {
  try {
    await confirmAction(
      $t('system.onlineUser.revokeContent', [row.email]),
      $t('system.onlineUser.revokeTitle'),
    );
    await revokeUserSessionApi(row.id);
    message.success($t('system.onlineUser.revokeSuccess'));
    gridApi.query();
  } catch {
    // The confirmation dialog and request interceptor already show feedback.
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
          return await listUserSessionsApi({
            keyword: buildKeyword(formValues.keyword),
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
  } as VxeTableGridOptions<UserSessionRecord>,
});
</script>

<template>
  <Page auto-content-height>
    <Grid :table-title="$t('system.onlineUser.list')" />
  </Page>
</template>
