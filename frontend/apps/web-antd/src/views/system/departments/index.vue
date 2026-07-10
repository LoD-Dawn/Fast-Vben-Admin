<script lang="ts" setup>
import type {
  OnActionClickParams,
  VxeTableGridOptions,
} from '#/adapter/vxe-table';
import type { DepartmentRecord } from '#/api';

import { ref } from 'vue';

import { Page, useVbenModal } from '@vben/common-ui';
import { Plus } from '@vben/icons';

import { Button, message } from 'ant-design-vue';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { deleteDepartmentApi, listDepartmentsApi } from '#/api';

import { useColumns } from './data';
import Form from './modules/form.vue';

const departments = ref<DepartmentRecord[]>([]);

const [FormModal, formModalApi] = useVbenModal({
  connectedComponent: Form,
  destroyOnClose: true,
});

function onActionClick({ code, row }: OnActionClickParams<DepartmentRecord>) {
  switch (code) {
    case 'append': {
      onAppend(row);
      break;
    }
    case 'delete': {
      void onDelete(row);
      break;
    }
    case 'edit': {
      formModalApi.setData(row).open();
      break;
    }
  }
}

function onAppend(row: DepartmentRecord) {
  formModalApi.setData({ parent_id: row.id }).open();
}

async function onDelete(row: DepartmentRecord) {
  const hideLoading = message.loading({
    content: `正在删除 ${row.name}`,
    duration: 0,
    key: 'dept_delete',
  });
  try {
    await deleteDepartmentApi(row.id);
    message.success({
      content: `${row.name} 已删除`,
      key: 'dept_delete',
    });
    onRefresh();
  } catch {
    hideLoading();
  }
}

const [Grid, gridApi] = useVbenVxeGrid({
  gridOptions: {
    columns: useColumns(
      onActionClick,
      (departmentId?: null | string) =>
        departments.value.some(
          (department) => department.parent_id === departmentId,
        ),
    ),
    height: 'auto',
    keepSource: true,
    pagerConfig: {
      enabled: false,
    },
    proxyConfig: {
      ajax: {
        query: async () => {
          const result = await listDepartmentsApi({
            page: 1,
            page_size: 500,
          });
          departments.value = result.items;
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
      zoom: true,
    },
    treeConfig: {
      parentField: 'parent_id',
      rowField: 'id',
      transform: true,
    },
  } as VxeTableGridOptions<DepartmentRecord>,
});

function onRefresh() {
  gridApi.query();
}

function onCreate() {
  formModalApi.setData(undefined).open();
}
</script>

<template>
  <Page auto-content-height>
    <FormModal @success="onRefresh" />
    <Grid table-title="部门列表">
      <template #toolbar-tools>
        <Button v-access:code="'system:department:create'" type="primary" @click="onCreate">
          <Plus class="size-5" />
          新增部门
        </Button>
      </template>
    </Grid>
  </Page>
</template>
