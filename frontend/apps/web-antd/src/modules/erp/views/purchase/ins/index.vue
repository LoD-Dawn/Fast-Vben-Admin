<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type {
  CounterpartyRecord,
  DocumentQuery,
  PurchaseInRecord,
  PurchaseOrderRecord,
  ProductRecord,
  SettlementAccountRecord,
  WarehouseRecord,
} from '#/modules/erp/api/erp';

import { computed, onMounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';

import { Page } from '@vben/common-ui';
import { Plus } from '@vben/icons';
import { Button, Drawer, Input, InputNumber, Popconfirm, Select, Space, Tag } from 'ant-design-vue';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import DocumentAttachmentButton from '#/modules/erp/components/document-attachment-button.vue';
import DocumentListFilters from '#/modules/erp/components/document-list-filters.vue';
import ExportCsvButton from '#/modules/erp/components/export-csv-button.vue';
import ReverseDocumentDialog from '#/modules/erp/components/reverse-document-dialog.vue';
import {
  approvePurchaseInApi,
  createPurchaseInApi,
  deletePurchaseInApi,
  listCounterpartiesApi,
  getPurchaseOrderApi,
  listPurchaseInsApi,
  listPurchaseOrdersApi,
  listProductsApi,
  listSettlementAccountsApi,
  listWarehousesApi,
  reversePurchaseInApi,
  updatePurchaseInApi,
} from '#/modules/erp/api/erp';
import ErpRemoteSelect from '#/modules/erp/components/erp-remote-select.vue';
import { compareDecimal, normalizeDecimal, subtractDecimal, QUANTITY_DECIMAL_PLACES } from '#/modules/erp/utils/decimal';

interface ReceiptLine {
  purchase_order_item_id: string;
  quantity: string;
  warehouse_id?: string;
}

const drawerOpen = ref(false);
const saving = ref(false);
const reverseOpen = ref(false);
const reverseTarget = ref<PurchaseInRecord>();
const editingReceipt = ref<PurchaseInRecord>();
const selectedOrderId = ref<string>();
const settlementAccountId = ref<string>();
const businessAt = ref<string>();
const discountRate = ref(0);
const discountAmount = ref<number>();
const otherFee = ref(0);
const purchaseOrders = ref<PurchaseOrderRecord[]>([]);
const warehouses = ref<WarehouseRecord[]>([]);
const settlementAccounts = ref<SettlementAccountRecord[]>([]);
const receiptLines = ref<ReceiptLine[]>([]);
const products = ref<ProductRecord[]>([]);
const suppliers = ref<CounterpartyRecord[]>([]);
const listQuery = ref<DocumentQuery>({});
const route = useRoute();
const exportQuery = computed(() =>
  Object.fromEntries(
    Object.entries(listQuery.value).filter(
      (entry): entry is [string, string] =>
        typeof entry[1] === 'string' && Boolean(entry[1]),
    ),
  ),
);

const selectedOrder = computed(() =>
  purchaseOrders.value.find((order) => order.id === selectedOrderId.value),
);

const [Grid, gridApi] = useVbenVxeGrid({
  gridOptions: {
    columns: [
      { field: 'no', minWidth: 190, title: '采购入库单号' },
      { field: 'purchase_order_no', minWidth: 190, title: '来源采购订单' },
      { field: 'supplier_name', minWidth: 160, title: '供应商' },
      { field: 'business_at', title: '入库日期', width: 180 },
      { field: 'total_quantity', title: '入库数量', width: 110 },
      { field: 'status', slots: { default: 'status' }, title: '状态', width: 90 },
      { field: 'version', title: '版本', width: 70 },
      { align: 'center', field: 'operation', fixed: 'right', slots: { default: 'operation' }, title: '操作', width: 150 },
    ],
    height: 'auto',
    proxyConfig: { ajax: { query: async ({ page }) => await listPurchaseInsApi({ ...listQuery.value, page: page.currentPage, page_size: page.pageSize }) } },
    rowConfig: { keyField: 'id' },
    toolbarConfig: { custom: true, refresh: true, zoom: true },
  } as VxeTableGridOptions<PurchaseInRecord>,
});

async function loadFilterReferences() {
  const [supplierResult, productResult] = await Promise.all([
    listCounterpartiesApi('supplier', { page: 1, page_size: 50 }),
    listProductsApi({ page: 1, page_size: 50 }),
  ]);
  suppliers.value = supplierResult.items.filter((item) => item.is_active);
  products.value = productResult.items.filter((item) => item.is_active);
}

onMounted(() => {
  void loadFilterReferences();
});

watch(
  () => route.query.purchase_order_id,
  (orderId) => {
    if (typeof orderId === 'string') void openCreateFromPurchaseOrder(orderId);
  },
  { immediate: true },
);

async function loadSuppliers(keyword: string) {
  const result = await listCounterpartiesApi('supplier', { keyword, page: 1, page_size: 50 });
  suppliers.value = result.items.filter((item) => item.is_active);
  return suppliers.value;
}

async function loadProducts(keyword: string) {
  const result = await listProductsApi({ keyword, page: 1, page_size: 50 });
  products.value = result.items.filter((item) => item.is_active);
  return products.value;
}

function remainingQuantity(item: NonNullable<PurchaseOrderRecord['items']>[number]) {
  return subtractDecimal(item.quantity, item.received_quantity, QUANTITY_DECIMAL_PLACES);
}

function formatOrder(order: PurchaseOrderRecord) { return { label: `${order.no} - ${order.supplier_name}`, value: order.id }; }
function formatWarehouse(warehouse: WarehouseRecord) { return { label: `${warehouse.name} (${warehouse.code})`, value: warehouse.id }; }
function formatSettlementAccount(account: SettlementAccountRecord) { return { label: account.name, value: account.id }; }
async function loadPurchaseOrders(keyword: string) {
  const result = await listPurchaseOrdersApi({ keyword, page: 1, page_size: 50 });
  purchaseOrders.value = result.items.filter((order) => order.status === 'approved' && (order.items ?? []).some((item) => compareDecimal(remainingQuantity(item), 0) > 0));
  return purchaseOrders.value;
}
async function loadWarehouses(keyword: string) {
  const result = await listWarehousesApi({ keyword, page: 1, page_size: 50 });
  warehouses.value = result.items.filter((warehouse) => warehouse.is_active);
  return warehouses.value;
}
async function loadSettlementAccounts(keyword: string) {
  const result = await listSettlementAccountsApi({ keyword, page: 1, page_size: 50 });
  settlementAccounts.value = result.items.filter((account) => account.is_active);
  return settlementAccounts.value;
}

function selectOrder(orderId: unknown) {
  if (typeof orderId !== 'string') return;
  const order = purchaseOrders.value.find((entry) => entry.id === orderId);
  settlementAccountId.value = order?.settlement_account_id || undefined;
  receiptLines.value = (order?.items ?? [])
    .filter((item) => compareDecimal(remainingQuantity(item), 0) > 0)
    .map((item) => ({
      purchase_order_item_id: item.id,
      quantity: remainingQuantity(item),
    }));
}

async function openCreate() {
  selectedOrderId.value = undefined;
  settlementAccountId.value = undefined;
  businessAt.value = undefined;
  discountRate.value = 0;
  discountAmount.value = undefined;
  otherFee.value = 0;
  receiptLines.value = [];
  editingReceipt.value = undefined;
  drawerOpen.value = true;
}

async function openCreateFromPurchaseOrder(orderId: string) {
  await openCreate();
  const order = await getPurchaseOrderApi(orderId);
  purchaseOrders.value = [order];
  selectedOrderId.value = order.id;
  selectOrder(order.id);
}

async function openEdit(row: PurchaseInRecord) {
  await openCreate();
  editingReceipt.value = row;
  const order = await getPurchaseOrderApi(row.purchase_order_id);
  purchaseOrders.value = [order];
  selectedOrderId.value = row.purchase_order_id;
  settlementAccountId.value = row.settlement_account_id || undefined;
  businessAt.value = new Date(row.business_at).toISOString().slice(0, 16);
  discountRate.value = Number(row.discount_rate);
  discountAmount.value = Number(row.discount_amount);
  otherFee.value = Number(row.other_fee);
  receiptLines.value = (row.items || []).map((line) => ({ purchase_order_item_id: line.purchase_order_item_id, quantity: normalizeDecimal(line.quantity, QUANTITY_DECIMAL_PLACES), warehouse_id: line.warehouse_id }));
}

async function submit() {
  if (!selectedOrder.value || receiptLines.value.length === 0 || receiptLines.value.some((line) => !line.warehouse_id || compareDecimal(line.quantity, 0) <= 0)) return;
  saving.value = true;
  try {
    const payload = {
      purchase_order_id: selectedOrder.value.id,
      settlement_account_id: settlementAccountId.value,
      business_at: businessAt.value ? new Date(businessAt.value).toISOString() : undefined,
      discount_rate: String(discountRate.value || 0),
      discount_amount: discountAmount.value === undefined ? undefined : String(discountAmount.value),
      other_fee: String(otherFee.value || 0),
      items: receiptLines.value.map((line) => ({
        purchase_order_item_id: line.purchase_order_item_id,
        quantity: normalizeDecimal(line.quantity, QUANTITY_DECIMAL_PLACES),
        warehouse_id: line.warehouse_id!,
      })),
    };
    if (editingReceipt.value) await updatePurchaseInApi(editingReceipt.value.id, payload, editingReceipt.value.version);
    else await createPurchaseInApi(payload);
    drawerOpen.value = false;
    gridApi.query();
  } finally {
    saving.value = false;
  }
}

async function remove(row: PurchaseInRecord) { await deletePurchaseInApi(row.id); gridApi.query(); }

async function approve(row: PurchaseInRecord) {
  await approvePurchaseInApi(row.id, row.version);
  gridApi.query();
}

function openReverse(row: PurchaseInRecord) {
  reverseTarget.value = row;
  reverseOpen.value = true;
}
async function confirmReverse(reason: string) {
  const row = reverseTarget.value;
  if (!row) return;
  await reversePurchaseInApi(row.id, row.version, reason);
  gridApi.query();
}
</script>

<template>
  <Page auto-content-height>
    <ReverseDocumentDialog v-model:open="reverseOpen" impact="反审核会回退本次入库库存；已有采购退货时将被后端阻止。" :on-confirm="confirmReverse" title="反审核采购入库" />
    <Drawer v-model:open="drawerOpen" :confirm-loading="saving" :title="editingReceipt ? '编辑采购入库' : '新建采购入库'" placement="right" width="min(1040px, 100vw)">
      <div class="mb-4">
        <div class="mb-1 text-sm font-medium">来源采购订单</div>
        <ErpRemoteSelect v-model:value="selectedOrderId" class="w-full" :format-option="formatOrder" :load="loadPurchaseOrders" placeholder="选择已审核且有剩余数量的采购订单" @change="selectOrder" />
      </div>
      <div v-if="selectedOrder" class="mb-3 text-sm text-[var(--vben-text-color-secondary)]">供应商：{{ selectedOrder.supplier_name }}，单据：{{ selectedOrder.no }}</div>
      <div class="mb-4 grid gap-3 md:grid-cols-4">
        <Input v-model:value="businessAt" type="datetime-local" />
        <ErpRemoteSelect v-model:value="settlementAccountId" allow-clear :format-option="formatSettlementAccount" :load="loadSettlementAccounts" placeholder="结算账户" />
        <InputNumber v-model:value="discountRate" :max="100" :min="0" :precision="4" placeholder="优惠率 (%)" />
        <InputNumber v-model:value="discountAmount" :min="0" :precision="4" placeholder="优惠金额" />
      </div>
      <div class="mb-4 max-w-56"><InputNumber v-model:value="otherFee" :min="0" :precision="4" class="w-full" placeholder="其他费用" /></div>
      <div class="overflow-x-auto rounded border border-[var(--vben-border-color)]">
        <table class="min-w-[820px] w-full text-left text-sm">
          <thead><tr><th class="p-2">商品</th><th class="p-2">订单数量</th><th class="p-2">可入库</th><th class="p-2">本次入库</th><th class="p-2">入库仓库</th></tr></thead>
          <tbody><tr v-for="line in receiptLines" :key="line.purchase_order_item_id" class="border-t border-[var(--vben-border-color)]"><td class="p-2">{{ selectedOrder?.items?.find((item) => item.id === line.purchase_order_item_id)?.product_name }}</td><td class="p-2">{{ selectedOrder?.items?.find((item) => item.id === line.purchase_order_item_id)?.quantity }}</td><td class="p-2">{{ remainingQuantity(selectedOrder?.items?.find((item) => item.id === line.purchase_order_item_id)!) }}</td><td class="p-2"><InputNumber v-model:value="line.quantity" :max="remainingQuantity(selectedOrder?.items?.find((item) => item.id === line.purchase_order_item_id)!)" :min="'0.000001'" :precision="6" string-mode /></td><td class="p-2"><ErpRemoteSelect v-model:value="line.warehouse_id" class="min-w-64" :format-option="formatWarehouse" :load="loadWarehouses" placeholder="选择仓库" /></td></tr></tbody>
        </table>
      </div>
      <template #footer><Button @click="drawerOpen = false">取消</Button><Button :loading="saving" type="primary" @click="submit">{{ editingReceipt ? '保存修改' : '保存草稿' }}</Button></template>
    </Drawer>
    <DocumentListFilters
      v-model="listQuery"
      :counterparties="suppliers"
      :counterparty-loader="loadSuppliers"
      counterparty-key="supplier_id"
      counterparty-label="供应商"
      :products="products"
      :product-loader="loadProducts"
      @query="gridApi.query()"
    />
    <Grid table-title="采购入库">
      <template #toolbar-tools><ExportCsvButton file-name="purchase-ins.csv" permission="erp:purchase-in:export" :query="exportQuery" resource="purchase-in" /><Button v-access:code="'erp:purchase-in:create'" type="primary" @click="openCreate"><Plus class="size-5" />新建采购入库</Button></template>
      <template #status="{ row }"><Tag :color="row.status === 'approved' ? 'green' : 'gold'">{{ row.status === 'approved' ? '已审核' : '草稿' }}</Tag></template>
      <template #operation="{ row }"><Space><DocumentAttachmentButton :document-id="row.id" document-type="purchase_in" /><Button v-if="row.status === 'draft'" v-access:code="'erp:purchase-in:update'" size="small" type="link" @click="openEdit(row)">编辑</Button><Popconfirm v-if="row.status === 'draft'" title="确认删除该草稿采购入库单？" @confirm="remove(row)"><Button v-access:code="'erp:purchase-in:delete'" danger size="small" type="link">删除</Button></Popconfirm><Popconfirm v-if="row.status === 'draft'" title="审核后将增加库存并占用采购订单剩余数量。确定继续吗？" @confirm="approve(row)"><Button v-access:code="'erp:purchase-in:approve'" size="small" type="link">审核</Button></Popconfirm><Button v-else v-access:code="'erp:purchase-in:reverse'" size="small" type="link" @click="openReverse(row)">反审核</Button></Space></template>
    </Grid>
  </Page>
</template>
