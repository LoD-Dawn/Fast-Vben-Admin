<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type {
  SettlementAccountPayload,
  SettlementAccountRecord,
} from '#/modules/erp/api/erp';

import { reactive, ref } from 'vue';

import { Page } from '@vben/common-ui';
import { Plus } from '@vben/icons';
import {
  Button,
  Drawer,
  Form,
  Input,
  InputNumber,
  Popconfirm,
  Space,
  Switch,
  Tag,
} from 'ant-design-vue';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import ExportCsvButton from '#/modules/erp/components/export-csv-button.vue';
import {
  createSettlementAccountApi,
  deleteSettlementAccountApi,
  listSettlementAccountsApi,
  updateSettlementAccountApi,
} from '#/modules/erp/api/erp';

interface AccountForm {
  account_no?: string;
  is_active: boolean;
  is_default: boolean;
  name: string;
  remark?: string;
  sort: number | undefined;
}

const drawerOpen = ref(false);
const saving = ref(false);
const editingId = ref<string>();
const form = reactive<AccountForm>({
  account_no: undefined,
  is_active: true,
  is_default: false,
  name: '',
  remark: undefined,
  sort: 0,
});

const [Grid, gridApi] = useVbenVxeGrid({
  gridOptions: {
    columns: [
      { field: 'name', minWidth: 180, title: '账户名称' },
      { field: 'account_no_masked', minWidth: 150, title: '账号' },
      { field: 'is_default', slots: { default: 'default' }, title: '默认', width: 90 },
      { field: 'is_active', slots: { default: 'status' }, title: '状态', width: 90 },
      { field: 'sort', title: '排序', width: 80 },
      { field: 'remark', minWidth: 200, showOverflow: true, title: '备注' },
      { align: 'center', field: 'operation', fixed: 'right', slots: { default: 'operation' }, title: '操作', width: 130 },
    ],
    height: 'auto',
    proxyConfig: {
      ajax: {
        query: async ({ page }) =>
          await listSettlementAccountsApi({
            page: page.currentPage,
            page_size: page.pageSize,
          }),
      },
    },
    rowConfig: { keyField: 'id' },
    toolbarConfig: { custom: true, refresh: true, zoom: true },
  } as VxeTableGridOptions<SettlementAccountRecord>,
});

function resetForm() {
  editingId.value = undefined;
  Object.assign(form, {
    account_no: undefined,
    is_active: true,
    is_default: false,
    name: '',
    remark: undefined,
    sort: 0,
  });
}

function openCreate() {
  resetForm();
  drawerOpen.value = true;
}

function openEdit(record: SettlementAccountRecord) {
  editingId.value = record.id;
  Object.assign(form, {
    account_no: undefined,
    is_active: record.is_active,
    is_default: record.is_default,
    name: record.name,
    remark: record.remark ?? undefined,
    sort: record.sort,
  });
  drawerOpen.value = true;
}

async function submit() {
  if (!form.name.trim() || (!editingId.value && !form.account_no?.trim())) return;
  saving.value = true;
  try {
    const payload: SettlementAccountPayload = {
      is_active: form.is_active,
      is_default: form.is_default,
      name: form.name.trim(),
      remark: form.remark?.trim() || undefined,
      sort: form.sort ?? 0,
    };
    if (form.account_no?.trim()) payload.account_no = form.account_no.trim();
    if (editingId.value) await updateSettlementAccountApi(editingId.value, payload);
    else await createSettlementAccountApi(payload as Required<SettlementAccountPayload>);
    drawerOpen.value = false;
    gridApi.query();
  } finally {
    saving.value = false;
  }
}

async function remove(record: SettlementAccountRecord) {
  await deleteSettlementAccountApi(record.id);
  gridApi.query();
}
</script>

<template>
  <Page auto-content-height>
    <Drawer v-model:open="drawerOpen" :confirm-loading="saving" :title="editingId ? '编辑结算账户' : '新建结算账户'" placement="right" width="min(520px, 100vw)">
      <Form :label-col="{ span: 6 }" :model="form" :wrapper-col="{ span: 16 }" layout="horizontal">
        <Form.Item label="账户名称" required><Input v-model:value="form.name" :maxlength="200" /></Form.Item>
        <Form.Item :label="editingId ? '新账号' : '账号'" :required="!editingId"><Input v-model:value="form.account_no" autocomplete="off" :maxlength="500" /></Form.Item>
        <Form.Item label="排序"><InputNumber v-model:value="form.sort" :min="0" class="w-full" /></Form.Item>
        <Form.Item label="启用"><Switch v-model:checked="form.is_active" /></Form.Item>
        <Form.Item label="默认账户"><Switch v-model:checked="form.is_default" /></Form.Item>
        <Form.Item label="备注"><Input v-model:value="form.remark" :maxlength="500" /></Form.Item>
      </Form>
      <template #footer><Button @click="drawerOpen = false">取消</Button><Button :loading="saving" type="primary" @click="submit">保存</Button></template>
    </Drawer>
    <Grid table-title="结算账户">
      <template #toolbar-tools><ExportCsvButton file-name="settlement-accounts.csv" permission="erp:account:export" resource="account" /><Button v-access:code="'erp:account:create'" type="primary" @click="openCreate"><Plus class="size-5" />新建结算账户</Button></template>
      <template #default="{ row }"><Tag v-if="row.is_default" color="blue">默认</Tag><span v-else>-</span></template>
      <template #status="{ row }"><Tag :color="row.is_active ? 'green' : 'default'">{{ row.is_active ? '启用' : '停用' }}</Tag></template>
      <template #operation="{ row }"><Space><Button v-access:code="'erp:account:update'" size="small" type="link" @click="openEdit(row)">编辑</Button><Popconfirm title="确认删除结算账户？" @confirm="remove(row)"><Button v-access:code="'erp:account:delete'" danger size="small" type="link">删除</Button></Popconfirm></Space></template>
    </Grid>
  </Page>
</template>
