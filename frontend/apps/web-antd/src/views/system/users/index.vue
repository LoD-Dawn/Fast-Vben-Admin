<script lang="ts" setup>
import type {
  OnActionClickParams,
  VxeTableGridOptions,
} from '#/adapter/vxe-table';
import type { DepartmentRecord, UserRecord } from '#/api';

import { computed, onMounted, ref } from 'vue';

import { Page, Tree, useVbenDrawer, useVbenModal } from '@vben/common-ui';
import { IconifyIcon, Plus } from '@vben/icons';

import { Button, Card, InputSearch, message } from 'ant-design-vue';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  deleteUserApi,
  downloadApi,
  listDepartmentsApi,
  listUsersApi,
  updateUserApi,
  usersExportPath,
  usersImportTemplatePath,
} from '#/api';

import { $t } from '#/locales';

import { buildDepartmentTree, confirmAction } from '../shared/utils';
import { useColumns, useGridFormSchema } from './data';
import Form from './modules/form.vue';
import Import from './modules/import.vue';

const allDepartments = ref<DepartmentRecord[]>([]);
const deptSearchValue = ref('');
const selectedDeptId = ref<string>('');

const deptTreeData = computed(() => {
  const keyword = deptSearchValue.value.trim().toLowerCase();
  const source = keyword
    ? allDepartments.value.filter((department) =>
        department.name.toLowerCase().includes(keyword),
      )
    : allDepartments.value;
  return buildDepartmentTree(source);
});

const [FormDrawer, formDrawerApi] = useVbenDrawer({
  connectedComponent: Form,
  destroyOnClose: true,
});

const [ImportModal, importModalApi] = useVbenModal({
  connectedComponent: Import,
  destroyOnClose: true,
});

async function onStatusChange(newStatus: boolean, row: UserRecord) {
  try {
    await confirmAction(
      $t('system.user.toggleStatusContent', [
        row.email,
        newStatus ? $t('common.enabled') : $t('common.disabled'),
      ]),
      $t('system.user.toggleStatusTitle'),
    );
    await updateUserApi(row.id, { is_active: newStatus });
    return true;
  } catch {
    return false;
  }
}

function onActionClick({ code, row }: OnActionClickParams<UserRecord>) {
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

async function onDelete(row: UserRecord) {
  const hideLoading = message.loading({
    content: $t('system.user.deleting', [row.email]),
    duration: 0,
    key: 'user_delete',
  });
  try {
    await deleteUserApi(row.id);
    message.success({
      content: $t('system.user.deleteSuccess'),
      key: 'user_delete',
    });
    onRefresh();
  } catch {
    hideLoading();
  }
}

const [Grid, gridApi] = useVbenVxeGrid({
  formOptions: {
    fieldMappingTime: [['createTime', ['startTime', 'endTime']]],
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
          return await listUsersApi({
            department_id: selectedDeptId.value || undefined,
            is_active:
              formValues.is_active === undefined || formValues.is_active === null
                ? undefined
                : formValues.is_active,
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
  } as VxeTableGridOptions<UserRecord>,
});

function onRefresh() {
  gridApi.query();
}

function onCreate() {
  formDrawerApi.setData(undefined).open();
}

async function exportUsers() {
  await downloadApi(usersExportPath, 'users.csv');
}

async function downloadTemplate() {
  await downloadApi(usersImportTemplatePath, 'users-import-template.csv');
}

function openImport() {
  importModalApi.open();
}

function selectDept(item?: { value: DepartmentRecord }) {
  selectedDeptId.value = item?.value.id ?? '';
  gridApi.query();
}

function getDeptNodeIcon(
  department: DepartmentRecord & { children?: DepartmentRecord[] },
) {
  return department.children?.length ? 'lucide:folder' : 'lucide:file';
}

async function loadDepartments() {
  const result = await listDepartmentsApi({ page: 1, page_size: 500 });
  allDepartments.value = result.items;
}

onMounted(loadDepartments);
</script>

<template>
  <Page auto-content-height>
    <FormDrawer @success="onRefresh" />
    <ImportModal @success="onRefresh" />
    <div class="flex size-full">
      <Card :bordered="false" class="dept-tree-card w-1/6 min-w-[220px]">
        <InputSearch
          v-model:value="deptSearchValue"
          allow-clear
          class="mb-3"
          :placeholder="$t('system.user.placeholder')"
        />
        <div
          class="dept-tree-all mb-1 cursor-pointer py-1 text-sm"
          :class="{ 'dept-tree-all--active': !selectedDeptId }"
          @click="selectDept()"
        >
          {{ $t('system.dept.list') }}
        </div>
        <Tree
          v-model="selectedDeptId"
          class="dept-tree"
          :default-expanded-level="2"
          label-field="name"
          :show-icon="false"
          :transition="false"
          value-field="id"
          :tree-data="deptTreeData"
          @select="selectDept"
        >
          <template #node="{ value }">
            <span class="dept-tree-node">
              <IconifyIcon
                class="dept-tree-node__icon"
                :icon="getDeptNodeIcon(value)"
              />
              <span class="dept-tree-node__label">{{ value.name }}</span>
            </span>
          </template>
        </Tree>
      </Card>

      <div class="ml-4 w-5/6 min-w-0">
        <Grid :table-title="$t('system.user.list')">
          <template #toolbar-tools>
            <Button v-access:code="'system:user:create'" type="primary" @click="onCreate">
              <Plus class="size-5" />
              {{ $t('system.user.createUser') }}
            </Button>
            <Button v-access:code="'system:user:list'" class="ml-2" @click="exportUsers">
              {{ $t('system.user.export') }}
            </Button>
            <Button
              v-access:code="'system:user:create'"
              class="ml-2"
              @click="downloadTemplate"
            >
              {{ $t('system.user.template') }}
            </Button>
            <Button v-access:code="'system:user:create'" class="ml-2" @click="openImport">
              {{ $t('system.user.import') }}
            </Button>
          </template>
        </Grid>
      </div>
    </div>
  </Page>
</template>

<style scoped>
.dept-tree-card :deep(.ant-card-body) {
  padding: 12px;
}

.dept-tree-all {
  color: hsl(var(--foreground) / 80%);
  line-height: 1.75;
}

.dept-tree-all--active {
  color: hsl(var(--foreground));
  text-decoration: underline;
  text-underline-offset: 2px;
}

.dept-tree :deep(.container) {
  font-weight: 400;
  border-radius: 0;
}

.dept-tree :deep(.tree-node) {
  margin: 0;
  padding: 4px 0;
  border-radius: 0;
  line-height: 1.75;
}

.dept-tree :deep(.tree-node[data-selected]) {
  background: transparent;
}

.dept-tree :deep(.tree-node[data-selected] .dept-tree-node__label) {
  color: hsl(var(--foreground));
  text-decoration: underline;
  text-underline-offset: 2px;
}

.dept-tree :deep(.tree-node:hover) {
  background: transparent;
}

.dept-tree :deep(.tree-node > svg:first-child) {
  width: 10px;
  height: 10px;
  flex-shrink: 0;
  margin-right: 2px;
  color: hsl(var(--foreground) / 65%);
  stroke-width: 2.5px;
}

.dept-tree-node {
  display: inline-flex;
  min-width: 0;
  align-items: center;
  gap: 4px;
}

.dept-tree-node__icon {
  flex-shrink: 0;
  width: 16px;
  height: 16px;
  color: hsl(var(--foreground) / 70%);
}

.dept-tree-node__label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: hsl(var(--foreground) / 85%);
}
</style>
