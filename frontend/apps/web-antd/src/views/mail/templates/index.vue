<script lang="ts" setup>
import type {
  OnActionClickParams,
  VxeTableGridOptions,
} from '#/adapter/vxe-table';
import type { MailTemplateRecord } from '#/api';

import { Page, useVbenDrawer } from '@vben/common-ui';
import { Plus } from '@vben/icons';

import { Button, message } from 'ant-design-vue';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  deleteMailTemplateApi,
  listMailTemplatesApi,
  updateMailTemplateApi,
} from '#/api';

import { confirmAction } from '../../system/shared/utils';
import { useColumns, useGridFormSchema } from './data';
import Form from './modules/form.vue';
import Send from './modules/send.vue';

const [FormDrawer, formDrawerApi] = useVbenDrawer({
  connectedComponent: Form,
  destroyOnClose: true,
});

const [SendDrawer, sendDrawerApi] = useVbenDrawer({
  connectedComponent: Send,
  destroyOnClose: true,
});

async function onStatusChange(newStatus: boolean, row: MailTemplateRecord) {
  try {
    await confirmAction(
      `确认将邮件模板 ${row.name} 切换为【${newStatus ? '启用' : '禁用'}】吗？`,
      '切换状态',
    );
    await updateMailTemplateApi(row.id, { is_active: newStatus });
    return true;
  } catch {
    return false;
  }
}

function onActionClick({ code, row }: OnActionClickParams<MailTemplateRecord>) {
  if (code === 'edit') {
    formDrawerApi.setData(row).open();
  }
  if (code === 'send') {
    sendDrawerApi.setData(row).open();
  }
  if (code === 'delete') {
    void onDelete(row);
  }
}

async function onDelete(row: MailTemplateRecord) {
  try {
    await confirmAction(`确认删除邮件模板 ${row.name} 吗？`, '删除邮件模板');
    await deleteMailTemplateApi(row.id);
    message.success('邮件模板已删除');
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
          return await listMailTemplatesApi({
            account_id: formValues.account_id || undefined,
            is_active: formValues.is_active,
            keyword: formValues.keyword || undefined,
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
  } as VxeTableGridOptions<MailTemplateRecord>,
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
    <SendDrawer />
    <Grid table-title="邮件模板">
      <template #toolbar-tools>
        <Button
          v-access:code="'system:mail-template:create'"
          type="primary"
          @click="onCreate"
        >
          <Plus class="size-5" />
          新增模板
        </Button>
      </template>
    </Grid>
  </Page>
</template>
