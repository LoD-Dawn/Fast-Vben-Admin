<script lang="ts" setup>
import type {
  OnActionClickParams,
  VxeTableGridOptions,
} from '#/adapter/vxe-table';
import type { MenuRecord } from '#/api';

import { Page, useVbenDrawer } from '@vben/common-ui';
import { IconifyIcon, Plus } from '@vben/icons';

import { Button, message } from 'ant-design-vue';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { deleteMenuApi, listMenusApi, updateMenuApi } from '#/api';

import { buildKeyword, confirmAction } from '../shared/utils';
import { useColumns, useGridFormSchema } from './data';
import Form from './modules/form.vue';

const [FormDrawer, formDrawerApi] = useVbenDrawer({
  connectedComponent: Form,
  destroyOnClose: true,
});

async function onStatusChange(newStatus: boolean, row: MenuRecord) {
  try {
    await confirmAction(
      `确认将菜单 ${row.title} 的状态切换为【${newStatus ? '启用' : '禁用'}】吗？`,
      '切换状态',
    );
    await updateMenuApi(row.id, { is_active: newStatus });
    return true;
  } catch {
    return false;
  }
}

function onActionClick({ code, row }: OnActionClickParams<MenuRecord>) {
  switch (code) {
    case 'delete': {
      void onDelete(row);
      break;
    }
    case 'edit': {
      formDrawerApi.setData(row).open();
      break;
    }
  }
}

async function onDelete(row: MenuRecord) {
  const hideLoading = message.loading({
    content: `正在删除 ${row.title}`,
    duration: 0,
    key: 'menu_delete',
  });
  try {
    await deleteMenuApi(row.id);
    message.success({
      content: `${row.title} 已删除`,
      key: 'menu_delete',
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
    columns: useColumns(onActionClick, onStatusChange),
    height: 'auto',
    keepSource: true,
    pagerConfig: {
      enabled: false,
    },
    proxyConfig: {
      ajax: {
        query: async (_params, formValues) => {
          const result = await listMenusApi({
            keyword: buildKeyword(formValues.keyword) || undefined,
            page: 1,
            page_size: 500,
          });
          return result.items;
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
    treeConfig: {
      parentField: 'parent_id',
      rowField: 'id',
      transform: true,
    },
  } as VxeTableGridOptions<MenuRecord>,
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
    <Grid table-title="菜单列表">
      <template #toolbar-tools>
        <Button v-access:code="'system:menu:create'" type="primary" @click="onCreate">
          <Plus class="size-5" />
          新增菜单
        </Button>
      </template>
      <template #title="{ row }">
        <div class="flex w-full items-center gap-1">
          <span class="flex size-5 shrink-0 items-center justify-center">
            <IconifyIcon
              v-if="row.type === 'button'"
              icon="carbon:security"
              class="size-4"
            />
            <IconifyIcon
              v-else-if="row.icon"
              :icon="row.icon"
              class="size-4"
            />
          </span>
          <span class="min-w-0 flex-auto truncate">{{ row.title }}</span>
        </div>
      </template>
    </Grid>
  </Page>
</template>
