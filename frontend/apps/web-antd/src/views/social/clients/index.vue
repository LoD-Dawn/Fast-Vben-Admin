<script lang="ts" setup>
import type {
  OnActionClickParams,
  VxeTableGridOptions,
} from '#/adapter/vxe-table';
import type { SocialClientRecord } from '#/api';

import { Page, useVbenDrawer } from '@vben/common-ui';
import { Plus } from '@vben/icons';

import { Button, message } from 'ant-design-vue';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  deleteSocialClientApi,
  listSocialClientsApi,
  updateSocialClientApi,
} from '#/api';

import { confirmAction } from '../../system/shared/utils';
import { useColumns, useGridFormSchema } from './data';
import Form from './modules/form.vue';

const [FormDrawer, formDrawerApi] = useVbenDrawer({
  connectedComponent: Form,
  destroyOnClose: true,
});

async function onStatusChange(
  newStatus: boolean,
  row: SocialClientRecord,
) {
  try {
    await confirmAction(
      `确认将三方登录客户端 ${row.name} 切换为【${newStatus ? '启用' : '禁用'}】吗？`,
      '切换状态',
    );
    await updateSocialClientApi(row.id, { is_active: newStatus });
    return true;
  } catch {
    return false;
  }
}

function onActionClick({ code, row }: OnActionClickParams<SocialClientRecord>) {
  if (code === 'edit') {
    formDrawerApi.setData(row).open();
  }
  if (code === 'delete') {
    void onDelete(row);
  }
}

async function onDelete(row: SocialClientRecord) {
  try {
    await confirmAction(`确认删除三方登录客户端 ${row.name} 吗？`, '删除客户端');
    await deleteSocialClientApi(row.id);
    message.success('三方登录客户端已删除');
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
    columns: useColumns(onActionClick, onStatusChange),
    height: 'auto',
    keepSource: true,
    proxyConfig: {
      ajax: {
        query: async ({ page }, formValues) => {
          return await listSocialClientsApi({
            is_active: formValues.is_active,
            keyword: formValues.keyword || undefined,
            page: page.currentPage,
            page_size: page.pageSize,
            social_type: formValues.social_type || undefined,
            user_type: formValues.user_type || undefined,
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
  } as VxeTableGridOptions<SocialClientRecord>,
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
    <Grid table-title="三方登录客户端管理">
      <template #toolbar-tools>
        <Button
          v-access:code="'system:social-client:create'"
          type="primary"
          @click="onCreate"
        >
          <Plus class="size-5" />
          新增客户端
        </Button>
      </template>
    </Grid>
  </Page>
</template>
