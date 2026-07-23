<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type {
  ProductRecord,
  StockBalanceRecord,
  StockLedgerRecord,
  StockQuery,
} from '#/modules/erp/api/erp';

import { computed, ref, watch } from 'vue';
import { useRoute } from 'vue-router';

import { Page } from '@vben/common-ui';
import { Download } from '@vben/icons';
import { Button, Segmented } from 'ant-design-vue';

import { useVbenVxeGrid, VbenTableAction } from '#/adapter/vxe-table';
import { downloadApi } from '#/api';
import LedgerSourceDocument from '#/modules/erp/components/ledger-source-document.vue';
import {
  listProductCategoriesApi,
  listProductsApi,
  listStockBalancesApi,
  listStockRecordsApi,
  listWarehousesApi,
  stockBalancesExportPath,
  stockRecordsExportPath,
} from '#/modules/erp/api/erp';

const route = useRoute();

function viewForPath(path: string): 'balance' | 'ledger' {
  return path === '/erp/stock/ledger' ? 'ledger' : 'balance';
}

const view = ref<'balance' | 'ledger'>(viewForPath(route.path));
const isDedicatedPage = computed(
  () => route.path === '/erp/stock/balances' || route.path === '/erp/stock/ledger',
);

const ledgerTypeOptions = [
  { label: '采购入库', value: 'purchase_in' },
  { label: '采购入库冲销', value: 'purchase_in_reversal' },
  { label: '采购退货', value: 'purchase_return' },
  { label: '采购退货冲销', value: 'purchase_return_reversal' },
  { label: '销售出库', value: 'sale_out' },
  { label: '销售出库冲销', value: 'sale_out_reversal' },
  { label: '销售退货', value: 'sale_return' },
  { label: '销售退货冲销', value: 'sale_return_reversal' },
  { label: '其他入库', value: 'other_in' },
  { label: '其他入库冲销', value: 'other_in_reversal' },
  { label: '其他出库', value: 'other_out' },
  { label: '其他出库冲销', value: 'other_out_reversal' },
  { label: '调拨入库', value: 'move_in' },
  { label: '调拨入库冲销', value: 'move_in_reversal' },
  { label: '调拨出库', value: 'move_out' },
  { label: '调拨出库冲销', value: 'move_out_reversal' },
  { label: '库存盘点', value: 'check_gain' },
  { label: '盘盈冲销', value: 'check_gain_reversal' },
  { label: '盘亏', value: 'check_loss' },
  { label: '盘亏冲销', value: 'check_loss_reversal' },
];

async function loadProducts() {
  const result = await listProductsApi({ page: 1, page_size: 100 });
  return result.items;
}

async function loadCategories() {
  const result = await listProductCategoriesApi({ page: 1, page_size: 100 });
  return result.items;
}

async function loadWarehouses() {
  const result = await listWarehousesApi({ page: 1, page_size: 100 });
  return result.items;
}

const currentQuery = ref<StockQuery>({});

async function exportCurrentView() {
  const query = new URLSearchParams(
    Object.entries(currentQuery.value)
      .filter(
        ([, value]) => value !== undefined && value !== null && value !== '',
      )
      .map(([key, value]) => [key, String(value)]),
  ).toString();
  const path =
    view.value === 'balance' ? stockBalancesExportPath : stockRecordsExportPath;
  await downloadApi(
    `${path}${query ? `?${query}` : ''}`,
    view.value === 'balance' ? 'stock-balances.csv' : 'stock-records.csv',
  );
}

const [BalanceGrid, balanceGridApi] = useVbenVxeGrid({
  formOptions: {
    schema: [
      {
        component: 'ApiSelect',
        componentProps: {
          allowClear: true,
          api: loadProducts,
          class: 'w-full',
          labelFn: (p: ProductRecord) => `${p.code} - ${p.name}`,
          placeholder: '请选择商品',
          showSearch: true,
          valueField: 'id',
        },
        fieldName: 'product_id',
        label: '商品',
      },
      {
        component: 'ApiSelect',
        componentProps: {
          allowClear: true,
          api: loadCategories,
          class: 'w-full',
          labelField: 'name',
          placeholder: '请选择商品分类',
          showSearch: true,
          valueField: 'id',
        },
        fieldName: 'category_id',
        label: '商品分类',
      },
      {
        component: 'ApiSelect',
        componentProps: {
          allowClear: true,
          api: loadWarehouses,
          class: 'w-full',
          labelField: 'name',
          placeholder: '请选择仓库',
          showSearch: true,
          valueField: 'id',
        },
        fieldName: 'warehouse_id',
        label: '仓库',
      },
    ],
    showCollapseButton: true,
  },
  gridOptions: {
    columns: [
      { field: 'product_code', minWidth: 140, title: '商品编码' },
      { field: 'product_name', minWidth: 190, title: '商品名称' },
      { field: 'unit_name', title: '单位', width: 100 },
      { field: 'warehouse_name', minWidth: 160, title: '仓库' },
      { field: 'quantity', title: '可用数量', width: 130 },
      { field: 'updated_at', title: '最近记账', width: 180 },
      { align: 'center', field: 'operation', fixed: 'right', slots: { default: 'operation' }, title: '操作', width: 100 },
    ],
    height: 'auto',
    proxyConfig: {
      ajax: {
        query: async ({ page }, formValues) => {
          currentQuery.value = formValues;
          return await listStockBalancesApi({
            ...formValues,
            page: page.currentPage,
            page_size: page.pageSize,
          });
        },
      },
    },
    rowConfig: { keyField: 'id' },
    toolbarConfig: { custom: true, refresh: true, search: true, zoom: true },
  } as VxeTableGridOptions<StockBalanceRecord>,
});

const [LedgerGrid, ledgerGridApi] = useVbenVxeGrid({
  formOptions: {
    schema: [
      {
        component: 'ApiSelect',
        componentProps: {
          allowClear: true,
          api: loadProducts,
          class: 'w-full',
          labelFn: (p: ProductRecord) => `${p.code} - ${p.name}`,
          placeholder: '请选择商品',
          showSearch: true,
          valueField: 'id',
        },
        fieldName: 'product_id',
        label: '商品',
      },
      {
        component: 'ApiSelect',
        componentProps: {
          allowClear: true,
          api: loadCategories,
          class: 'w-full',
          labelField: 'name',
          placeholder: '请选择商品分类',
          showSearch: true,
          valueField: 'id',
        },
        fieldName: 'category_id',
        label: '商品分类',
      },
      {
        component: 'ApiSelect',
        componentProps: {
          allowClear: true,
          api: loadWarehouses,
          class: 'w-full',
          labelField: 'name',
          placeholder: '请选择仓库',
          showSearch: true,
          valueField: 'id',
        },
        fieldName: 'warehouse_id',
        label: '仓库',
      },
      {
        component: 'Select',
        componentProps: {
          allowClear: true,
          options: ledgerTypeOptions,
          placeholder: '请选择业务类型',
        },
        fieldName: 'ledger_type',
        label: '业务类型',
      },
      {
        component: 'Input',
        componentProps: { allowClear: true, placeholder: '请输入来源单号' },
        fieldName: 'source_document_no',
        label: '来源单号',
      },
    ],
    showCollapseButton: true,
  },
  gridOptions: {
    columns: [
      { field: 'occurred_at', title: '发生时间', width: 180 },
      { field: 'ledger_type', title: '业务类型', width: 150 },
      { field: 'product_code', minWidth: 140, title: '商品编码' },
      { field: 'product_name', minWidth: 190, title: '商品名称' },
      { field: 'warehouse_name', minWidth: 160, title: '仓库' },
      { field: 'delta_quantity', title: '变动数量', width: 120 },
      { field: 'balance_after', title: '结存数量', width: 120 },
      { field: 'source_document_no', minWidth: 170, slots: { default: 'sourceDocument' }, title: '来源单号' },
      { field: 'operator_name', minWidth: 130, title: '操作人' },
    ],
    height: 'auto',
    proxyConfig: {
      ajax: {
        query: async ({ page }, formValues) => {
          currentQuery.value = formValues;
          return await listStockRecordsApi({
            ...formValues,
            page: page.currentPage,
            page_size: page.pageSize,
          });
        },
      },
    },
    rowConfig: { keyField: 'id' },
    toolbarConfig: { custom: true, refresh: true, search: true, zoom: true },
  } as VxeTableGridOptions<StockLedgerRecord>,
});

function queryCurrentView() {
  (view.value === 'balance' ? balanceGridApi : ledgerGridApi).query();
}

watch(
  () => route.path,
  (path) => {
    if (!isDedicatedPage.value) return;
    view.value = viewForPath(path);
    queryCurrentView();
  },
);

async function openLedger(balance: StockBalanceRecord) {
  view.value = 'ledger';
  await ledgerGridApi.formApi.setValues({
    product_id: balance.product_id,
    warehouse_id: balance.warehouse_id,
  });
  ledgerGridApi.query();
}
</script>

<template>
  <Page auto-content-height>
    <div
      v-if="!isDedicatedPage"
      class="mb-3 flex items-center justify-between"
    >
      <Segmented
        v-model:value="view"
        :options="[
          { label: '库存余额', value: 'balance' },
          { label: '库存流水', value: 'ledger' },
        ]"
        @change="queryCurrentView"
      />
    </div>

    <BalanceGrid v-if="view === 'balance'" table-title="库存余额列表">
      <template #toolbar-tools>
        <div class="flex items-center gap-1">
          <Button
            v-access:code="'erp:stock:export'"
            class="gap-1"
            title="导出当前筛选"
            @click="exportCurrentView"
          >
            <Download class="size-4" />
            <span>导出</span>
          </Button>
        </div>
      </template>
      <template #operation="{ row }">
        <VbenTableAction
          :actions="[
            { auth: ['erp:stock-record:list'], icon: 'lucide:eye', onClick: openLedger.bind(null, row), text: '明细', variant: 'link' },
          ]"
        />
      </template>
    </BalanceGrid>

    <LedgerGrid v-else table-title="库存流水列表">
      <template #toolbar-tools>
        <div class="flex items-center gap-1">
          <Button
            v-access:code="'erp:stock-record:export'"
            class="gap-1"
            title="导出当前筛选"
            @click="exportCurrentView"
          >
            <Download class="size-4" />
            <span>导出</span>
          </Button>
        </div>
      </template>
      <template #sourceDocument="{ row }">
        <LedgerSourceDocument
          :document-id="row.source_document_id"
          :document-no="row.source_document_no"
          :document-type="row.source_document_type"
        />
      </template>
    </LedgerGrid>
  </Page>
</template>
