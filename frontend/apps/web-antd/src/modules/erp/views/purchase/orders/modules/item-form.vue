<script lang="ts" setup>
import type {
  ProductRecord,
  ProductUnitRecord,
} from '#/modules/erp/api/erp';
import type { PurchaseOrderLineForm } from '../data';

import { computed, nextTick, onMounted, ref, watch } from 'vue';

import { Input, InputNumber, Select } from 'ant-design-vue';

import { useVbenVxeGrid, VbenTableAction } from '#/adapter/vxe-table';
import {
  listProductsApi,
  listProductUnitsApi,
  listStockBalancesApi,
} from '#/modules/erp/api/erp';

import { useOrderItemColumns } from '../data';

interface Props {
  disabled?: boolean;
  discountRate?: number;
  items?: PurchaseOrderLineForm[];
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false,
  discountRate: 0,
  items: () => [],
});

const emit = defineEmits<{
  'update:discountAmount': [value: number];
  'update:items': [value: PurchaseOrderLineForm[]];
  'update:totalAmount': [value: number];
}>();

const tableData = ref<PurchaseOrderLineForm[]>([]);
const productOptions = ref<ProductRecord[]>([]);
const productUnits = ref<ProductUnitRecord[]>([]);

const summaries = computed(() => ({
  productAmount: tableData.value.reduce(
    (sum, item) => sum + Number(item.product_amount ?? 0),
    0,
  ),
  quantity: tableData.value.reduce(
    (sum, item) => sum + Number(item.quantity ?? 0),
    0,
  ),
  taxAmount: tableData.value.reduce(
    (sum, item) => sum + Number(item.tax_amount ?? 0),
    0,
  ),
  totalAmount: tableData.value.reduce(
    (sum, item) => sum + Number(item.total_amount ?? 0),
    0,
  ),
}));

const [Grid, gridApi] = useVbenVxeGrid({
  gridOptions: {
    autoResize: true,
    border: true,
    columns: useOrderItemColumns(props.disabled),
    data: [],
    minHeight: 250,
    pagerConfig: { enabled: false },
    rowConfig: { isHover: true, keyField: 'row_key' },
    toolbarConfig: { enabled: false },
  },
});

function formatAmount(value?: number) {
  return Number(value ?? 0).toFixed(2);
}

function formatQuantity(value?: number) {
  return Number(value ?? 0).toFixed(3);
}

function calculateRow(row: PurchaseOrderLineForm) {
  const quantity = Number(row.quantity ?? 0);
  const unitPrice = Number(row.unit_price ?? 0);
  row.product_amount = quantity * unitPrice;
  row.tax_amount = row.product_amount * (Number(row.tax_rate ?? 0) / 100);
  row.total_amount = row.product_amount + row.tax_amount;
}

function emitChanges() {
  emit('update:items', [...tableData.value]);
  emitTotals();
}

function emitTotals() {
  const grossAmount = tableData.value.reduce(
    (sum, item) => sum + Number(item.total_amount ?? 0),
    0,
  );
  const discountAmount =
    grossAmount * (Number(props.discountRate ?? 0) / 100);
  emit('update:discountAmount', discountAmount);
  emit('update:totalAmount', grossAmount - discountAmount);
}

async function loadStockQuantity(row: PurchaseOrderLineForm) {
  if (!row.product_id) return;
  try {
    const result = await listStockBalancesApi({
      page: 1,
      page_size: 200,
      product_id: row.product_id,
    });
    row.stock_quantity = result.items.reduce(
      (sum, item) => sum + Number(item.quantity),
      0,
    );
  } catch {
    row.stock_quantity = undefined;
  }
}

watch(
  () => props.items,
  async (items) => {
    tableData.value = items.map((item) => {
      const row = { ...item };
      calculateRow(row);
      return row;
    });
    await nextTick();
    await gridApi.grid.reloadData(tableData.value);
    await Promise.all(tableData.value.map(loadStockQuantity));
    await gridApi.grid.reloadData(tableData.value);
    emitTotals();
  },
  { immediate: true },
);

watch(
  () => props.discountRate,
  () => emitTotals(),
);

function handleAdd() {
  tableData.value.push({
    quantity: 1,
    row_key: crypto.randomUUID(),
    tax_rate: 0,
  });
  emitChanges();
}

function handleDelete(row: PurchaseOrderLineForm) {
  const index = tableData.value.findIndex(
    (item) => item.row_key === row.row_key,
  );
  if (index >= 0) tableData.value.splice(index, 1);
  emitChanges();
}

async function handleProductChange(
  productId: string,
  row: PurchaseOrderLineForm,
) {
  const product = productOptions.value.find((item) => item.id === productId);
  if (!product) return;
  row.product_id = product.id;
  row.product_name = product.name;
  row.product_barcode = product.barcode || undefined;
  row.unit_name = productUnits.value.find(
    (unit) => unit.id === product.unit_id,
  )?.name;
  row.unit_price = Number(product.purchase_reference_price ?? 0);
  row.quantity = row.quantity || 1;
  await loadStockQuantity(row);
  calculateRow(row);
  emitChanges();
}

function handleRowChange(row: PurchaseOrderLineForm) {
  calculateRow(row);
  emitChanges();
}

function validate() {
  if (tableData.value.length === 0) {
    throw new Error('请至少添加一个采购产品');
  }
  for (let index = 0; index < tableData.value.length; index += 1) {
    const item = tableData.value[index];
    if (!item?.product_id) {
      throw new Error(`第 ${index + 1} 行：产品不能为空`);
    }
    if (!item.quantity || item.quantity <= 0) {
      throw new Error(`第 ${index + 1} 行：产品数量必须大于 0`);
    }
    if (!item.unit_price || item.unit_price <= 0) {
      throw new Error(`第 ${index + 1} 行：产品单价必须大于 0`);
    }
  }
}

defineExpose({ validate });

onMounted(async () => {
  const [result, unitResult] = await Promise.all([
    listProductsApi({ page: 1, page_size: 200 }),
    listProductUnitsApi({ page: 1, page_size: 200 }),
  ]);
  productOptions.value = result.items.filter((item) => item.is_active);
  productUnits.value = unitResult.items.filter((item) => item.is_active);
  if (tableData.value.length === 0 && !props.disabled) handleAdd();
});
</script>

<template>
  <Grid class="w-full">
    <template #productId="{ row }">
      <Select
        v-if="!disabled"
        v-model:value="row.product_id"
        class="w-full"
        :field-names="{ label: 'name', value: 'id' }"
        option-filter-prop="name"
        :options="productOptions"
        placeholder="请选择产品"
        show-search
        @change="handleProductChange($event, row)"
      />
      <span v-else>{{ row.product_name || '-' }}</span>
    </template>
    <template #remark="{ row }">
      <Input
        v-if="!disabled"
        v-model:value="row.remark"
        class="w-full"
        :maxlength="500"
        @change="emitChanges"
      />
      <span v-else>{{ row.remark || '-' }}</span>
    </template>
    <template #quantity="{ row }">
      <InputNumber
        v-if="!disabled"
        v-model:value="row.quantity"
        :min="0"
        :precision="3"
        @change="handleRowChange(row)"
      />
      <span v-else>{{ formatQuantity(row.quantity) }}</span>
    </template>
    <template #unitPrice="{ row }">
      <InputNumber
        v-if="!disabled"
        v-model:value="row.unit_price"
        :min="0"
        :precision="2"
        @change="handleRowChange(row)"
      />
      <span v-else>{{ formatAmount(row.unit_price) }}</span>
    </template>
    <template #productAmount="{ row }">
      {{ formatAmount(row.product_amount) }}
    </template>
    <template #taxRate="{ row }">
      <InputNumber
        v-if="!disabled"
        v-model:value="row.tax_rate"
        :max="100"
        :min="0"
        :precision="2"
        @change="handleRowChange(row)"
      />
      <span v-else>{{ formatAmount(row.tax_rate) }}</span>
    </template>
    <template #taxAmount="{ row }">
      {{ formatAmount(row.tax_amount) }}
    </template>
    <template #totalAmount="{ row }">
      {{ formatAmount(row.total_amount) }}
    </template>
    <template #actions="{ row }">
      <VbenTableAction
        :actions="[
          {
            danger: true,
            popConfirm: {
              cancelText: '取消',
              confirm: handleDelete.bind(null, row),
              okText: '确认',
              title: '确认删除该产品吗？',
            },
            text: '删除',
            variant: 'link',
          },
        ]"
      />
    </template>

    <template #bottom>
      <div class="border-border bg-muted mt-2 rounded border p-2">
        <div
          class="text-muted-foreground flex items-center justify-between text-sm"
        >
          <span class="text-foreground font-medium">合计：</span>
          <div class="flex flex-wrap justify-end gap-x-4 gap-y-1">
            <span>数量：{{ formatQuantity(summaries.quantity) }}</span>
            <span>金额：{{ formatAmount(summaries.productAmount) }}</span>
            <span>税额：{{ formatAmount(summaries.taxAmount) }}</span>
            <span>税额合计：{{ formatAmount(summaries.totalAmount) }}</span>
          </div>
        </div>
      </div>
      <VbenTableAction
        v-if="!disabled"
        class="mt-2 flex justify-center"
        :actions="[
          {
            onClick: handleAdd,
            text: '添加采购产品',
            variant: 'default',
          },
        ]"
      />
    </template>
  </Grid>
</template>
