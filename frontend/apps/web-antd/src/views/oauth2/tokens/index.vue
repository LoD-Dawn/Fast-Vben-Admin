<script lang="ts" setup>
import type {
  OnActionClickParams,
  VxeTableGridOptions,
} from '#/adapter/vxe-table';
import type { OAuth2TokenRecord } from '#/api';

import { Page } from '@vben/common-ui';

import { message } from 'ant-design-vue';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { listOAuth2TokensApi, revokeOAuth2TokenApi } from '#/api';

import { confirmAction } from '../../system/shared/utils';
import { useColumns, useGridFormSchema } from './data';

function onActionClick({ code, row }: OnActionClickParams<OAuth2TokenRecord>) {
  if (code === 'revoke') {
    void onRevoke(row);
  }
}

async function onRevoke(row: OAuth2TokenRecord) {
  try {
    await confirmAction('确认吊销该 OAuth2 访问令牌吗？', '吊销令牌');
    await revokeOAuth2TokenApi(row.id);
    message.success('OAuth2 令牌已吊销');
    onRefresh();
  } catch {
    // 用户取消或接口失败时由全局错误处理接管
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
          return await listOAuth2TokensApi({
            client_id: formValues.client_id || undefined,
            keyword: formValues.keyword || undefined,
            page: page.currentPage,
            page_size: page.pageSize,
            revoked: formValues.revoked,
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
  } as VxeTableGridOptions<OAuth2TokenRecord>,
});

function onRefresh() {
  gridApi.query();
}
</script>

<template>
  <Page auto-content-height>
    <Grid table-title="OAuth2 令牌管理" />
  </Page>
</template>
