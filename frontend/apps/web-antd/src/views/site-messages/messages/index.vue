<script lang="ts" setup>
import type {
  OnActionClickParams,
  VxeTableGridOptions,
} from '#/adapter/vxe-table';
import type { SiteMessageRecord } from '#/api';

import { Page, useVbenDrawer } from '@vben/common-ui';

import { message } from 'ant-design-vue';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { deleteSiteMessageApi, listSiteMessagesApi } from '#/api';

import { confirmAction } from '../../system/shared/utils';
import { useColumns, useGridFormSchema } from './data';
import Detail from './modules/detail.vue';

const [DetailDrawer, detailDrawerApi] = useVbenDrawer({
  connectedComponent: Detail,
  destroyOnClose: true,
});

function onActionClick({ code, row }: OnActionClickParams<SiteMessageRecord>) {
  if (code === 'detail') {
    detailDrawerApi.setData(row).open();
  }
  if (code === 'delete') {
    void onDelete(row);
  }
}

async function onDelete(row: SiteMessageRecord) {
  try {
    await confirmAction(`确认删除站内信 ${row.title} 吗？`, '删除站内信');
    await deleteSiteMessageApi(row.id);
    message.success('站内信已删除');
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
          return await listSiteMessagesApi({
            is_read:
              formValues.is_read === undefined || formValues.is_read === null
                ? undefined
                : formValues.is_read,
            page: page.currentPage,
            page_size: page.pageSize,
            template_code: formValues.template_code || undefined,
            type: formValues.type || undefined,
            user_id: formValues.user_id || undefined,
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
  } as VxeTableGridOptions<SiteMessageRecord>,
});

function onRefresh() {
  gridApi.query();
}
</script>

<template>
  <Page auto-content-height>
    <DetailDrawer />
    <Grid table-title="站内信列表" />
  </Page>
</template>
