<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { FormInstance } from 'ant-design-vue';
import type { CounterpartyRecord } from '#/modules/erp/api/erp';

import { computed, reactive, ref, watch } from 'vue';
import { useRoute } from 'vue-router';

import { Page } from '@vben/common-ui';
import { IconifyIcon, Plus } from '@vben/icons';
import {
  Button,
  Drawer,
  Form,
  Input,
  InputNumber,
  Popconfirm,
  Segmented,
  Switch,
  Tag,
} from 'ant-design-vue';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import ExportCsvButton from '#/modules/erp/components/export-csv-button.vue';
import {
  createCounterpartyApi,
  deleteCounterpartyApi,
  listCounterpartiesApi,
  updateCounterpartyApi,
} from '#/modules/erp/api/erp';
import { buildKeyword } from '#/views/system/shared/utils';

type CounterpartyKind = 'customer' | 'supplier';

const route = useRoute();

function kindForPath(path: string): CounterpartyKind {
  return path === '/erp/sale/customers' ? 'customer' : 'supplier';
}

const kind = ref<CounterpartyKind>(kindForPath(route.path));
const isDedicatedPage = computed(() => route.path !== '/erp/counterparties');
const formRef = ref<FormInstance>();
const drawerOpen = ref(false);
const saving = ref(false);
const editingId = ref<string>();
const exportQuery = ref<Record<string, string | undefined>>({});
const form = reactive({
  address: undefined as string | undefined,
  bank_account: undefined as string | undefined,
  bank_name: undefined as string | undefined,
  contact_name: undefined as string | undefined,
  email: undefined as string | undefined,
  fax: undefined as string | undefined,
  is_active: true,
  mobile: undefined as string | undefined,
  name: '',
  phone: undefined as string | undefined,
  remark: undefined as string | undefined,
  sort: 0,
  tax_no: undefined as string | undefined,
  tax_rate: 0,
});

const labels: Record<CounterpartyKind, string> = {
  customer: '客户',
  supplier: '供应商',
};
const permissionPrefix: Record<CounterpartyKind, string> = {
  customer: 'erp:customer',
  supplier: 'erp:supplier',
};

const [Grid, gridApi] = useVbenVxeGrid({
  formOptions: {
    actionLayout: 'newLine',
    actionPosition: 'right',
    schema: [
      {
        component: 'Input',
        componentProps: {
          placeholder: `请输入${kind.value === 'supplier' ? '供应商' : '客户'}名称`,
        },
        fieldName: 'name',
        label: `${kind.value === 'supplier' ? '供应商' : '客户'}名称`,
      },
      {
        component: 'Input',
        componentProps: { placeholder: '请输入手机号码' },
        fieldName: 'mobile',
        label: '手机号码',
      },
      {
        component: 'Input',
        componentProps: { placeholder: '请输入联系电话' },
        fieldName: 'phone',
        label: '联系电话',
      },
    ],
    showCollapseButton: true,
    wrapperClass: 'grid-cols-1 gap-x-6 lg:grid-cols-3',
  },
  gridOptions: {
    columns: [
      {
        field: 'name',
        minWidth: 220,
        title: `${kind.value === 'supplier' ? '供应商' : '客户'}名称`,
      },
      { field: 'contact_name', minWidth: 180, title: '联系人' },
      { field: 'mobile', minWidth: 180, title: '手机号码' },
      { field: 'phone', minWidth: 180, title: '联系电话' },
      { field: 'email', minWidth: 220, title: '电子邮箱' },
      {
        field: 'is_active',
        slots: { default: 'status' },
        title: '状态',
        width: 90,
      },
      { field: 'sort', title: '排序', width: 100 },
      { field: 'remark', minWidth: 180, title: '备注' },
      {
        align: 'center',
        field: 'operation',
        fixed: 'right',
        slots: { default: 'operation' },
        title: '操作',
        width: 120,
      },
    ],
    height: 'auto',
    proxyConfig: {
      ajax: {
        query: async ({ page }, values) => {
          const query = {
            mobile: buildKeyword(values.mobile) || undefined,
            name: buildKeyword(values.name) || undefined,
            phone: buildKeyword(values.phone) || undefined,
          };
          exportQuery.value = query;
          return await listCounterpartiesApi(kind.value, {
            page: page.currentPage,
            page_size: page.pageSize,
            ...query,
          });
        },
      },
    },
    rowConfig: { keyField: 'id' },
    toolbarConfig: { custom: true, refresh: true, search: true, zoom: true },
  } as VxeTableGridOptions<CounterpartyRecord>,
});

function resetForm() {
  Object.assign(form, {
    address: undefined,
    bank_account: undefined,
    bank_name: undefined,
    contact_name: undefined,
    email: undefined,
    fax: undefined,
    is_active: true,
    mobile: undefined,
    name: '',
    phone: undefined,
    remark: undefined,
    sort: 0,
    tax_no: undefined,
    tax_rate: 0,
  });
  formRef.value?.clearValidate();
}

function openCreate() {
  editingId.value = undefined;
  resetForm();
  drawerOpen.value = true;
}

function openEdit(row: CounterpartyRecord) {
  editingId.value = row.id;
  resetForm();
  Object.assign(form, row);
  drawerOpen.value = true;
}

async function submit() {
  await formRef.value?.validate();
  saving.value = true;
  try {
    const payload = {
      ...form,
      address: form.address || null,
      bank_account: form.bank_account?.trim() || undefined,
      bank_name: form.bank_name || null,
      contact_name: form.contact_name || null,
      email: form.email || null,
      fax: form.fax || null,
      mobile: form.mobile || null,
      phone: form.phone || null,
      remark: form.remark || null,
      tax_no: form.tax_no || null,
      tax_rate: String(form.tax_rate),
    };
    if (editingId.value)
      await updateCounterpartyApi(kind.value, editingId.value, payload);
    else await createCounterpartyApi(kind.value, payload);
    drawerOpen.value = false;
    gridApi.query();
  } finally {
    saving.value = false;
  }
}

async function removeRecord(row: CounterpartyRecord) {
  await deleteCounterpartyApi(kind.value, row.id);
  gridApi.query();
}
function changeKind(value: CounterpartyKind) {
  kind.value = value;
  gridApi.query();
}

watch(
  () => route.path,
  (path) => {
    if (!isDedicatedPage.value) return;
    kind.value = kindForPath(path);
    gridApi.query();
  },
);
</script>

<template>
  <Page auto-content-height>
    <Drawer
      v-model:open="drawerOpen"
      :confirm-loading="saving"
      :title="`${editingId ? '编辑' : '新增'}${labels[kind]}`"
      placement="right"
      width="620"
      @close="resetForm"
    >
      <Form ref="formRef" :model="form" layout="vertical">
        <div class="grid grid-cols-2 gap-x-4">
          <Form.Item
            label="名称"
            name="name"
            :rules="[{ required: true, message: '请输入名称' }]"
            ><Input v-model:value="form.name" :maxlength="200"
          /></Form.Item>
          <Form.Item label="联系人"
            ><Input v-model:value="form.contact_name" :maxlength="100"
          /></Form.Item>
          <Form.Item label="手机"
            ><Input v-model:value="form.mobile" :maxlength="50"
          /></Form.Item>
          <Form.Item label="电话"
            ><Input v-model:value="form.phone" :maxlength="50"
          /></Form.Item>
          <Form.Item label="邮箱"
            ><Input v-model:value="form.email" :maxlength="320"
          /></Form.Item>
          <Form.Item label="传真"
            ><Input v-model:value="form.fax" :maxlength="50"
          /></Form.Item>
          <Form.Item label="税率 (%)"
            ><InputNumber
              v-model:value="form.tax_rate"
              :max="100"
              :min="0"
              :precision="4"
              class="w-full"
          /></Form.Item>
          <Form.Item label="税号"
            ><Input v-model:value="form.tax_no" :maxlength="100"
          /></Form.Item>
          <Form.Item label="开户行"
            ><Input v-model:value="form.bank_name" :maxlength="200"
          /></Form.Item>
          <Form.Item label="银行账号"
            ><Input
              v-model:value="form.bank_account"
              :maxlength="500"
              autocomplete="off"
              type="password"
          /></Form.Item>
          <Form.Item label="排序"
            ><InputNumber v-model:value="form.sort" :min="0" class="w-full"
          /></Form.Item>
          <Form.Item label="状态"
            ><Switch
              v-model:checked="form.is_active"
              checked-children="启用"
              un-checked-children="停用"
          /></Form.Item>
        </div>
        <Form.Item label="地址"
          ><Input.TextArea
            v-model:value="form.address"
            :maxlength="500"
            :rows="2"
        /></Form.Item>
        <Form.Item label="备注"
          ><Input.TextArea
            v-model:value="form.remark"
            :maxlength="500"
            :rows="2"
        /></Form.Item>
      </Form>
      <template #footer
        ><Button @click="drawerOpen = false">取消</Button
        ><Button :loading="saving" type="primary" @click="submit"
          >保存</Button
        ></template
      >
    </Drawer>
    <Segmented
      v-if="!isDedicatedPage"
      class="mb-3"
      :options="[
        { label: '供应商', value: 'supplier' },
        { label: '客户', value: 'customer' },
      ]"
      :value="kind"
      @change="changeKind($event as CounterpartyKind)"
    />
    <Grid :table-title="isDedicatedPage ? `${labels[kind]}列表` : '往来单位列表'">
      <template #toolbar-tools
        ><Button
          v-access:code="`${permissionPrefix[kind]}:create`"
          type="primary"
          @click="openCreate"
          ><Plus class="size-5" />新增{{ labels[kind] }}</Button
        ><ExportCsvButton
          :file-name="`${kind}s.csv`"
          :permission="`${permissionPrefix[kind]}:export`"
          :query="exportQuery"
          :resource="kind"
        />
      </template
      >
      <template #status="{ row }"
        ><Tag :color="row.is_active ? 'blue' : 'default'">{{
          row.is_active ? '开启' : '关闭'
        }}</Tag></template
      >
      <template #operation="{ row }"
        ><Button
          v-access:code="`${permissionPrefix[kind]}:update`"
          size="small"
          type="link"
          @click="openEdit(row)"
          ><IconifyIcon class="mr-1 size-4" icon="lucide:square-pen" />修改</Button
        ><Popconfirm
          title="删除后无法恢复。确定继续吗？"
          @confirm="removeRecord(row)"
          ><Button
            v-access:code="`${permissionPrefix[kind]}:delete`"
            danger
            size="small"
            type="link"
            ><IconifyIcon class="mr-1 size-4" icon="lucide:trash-2" />删除</Button
          ></Popconfirm
        ></template
      >
    </Grid>
  </Page>
</template>
