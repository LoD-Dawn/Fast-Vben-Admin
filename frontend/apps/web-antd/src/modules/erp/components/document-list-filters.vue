<script lang="ts" setup>
import type {
  CounterpartyRecord,
  DocumentQuery,
  ProductRecord,
  WarehouseRecord,
} from '#/modules/erp/api/erp';
import type { UserRecord } from '#/api';

import { computed, ref } from 'vue';

import { Input, Select } from 'ant-design-vue';

import { listUsersApi } from '#/api';
import ErpRemoteSelect from '#/modules/erp/components/erp-remote-select.vue';

const props = withDefaults(
  defineProps<{
    counterparties?: CounterpartyRecord[];
    counterpartyLoader?: (keyword: string) => Promise<CounterpartyRecord[]>;
    counterpartyKey?: 'customer_id' | 'supplier_id';
    counterpartyLabel?: string;
    modelValue: DocumentQuery;
    products?: ProductRecord[];
    productLoader?: (keyword: string) => Promise<ProductRecord[]>;
    showFulfillmentStatus?: boolean;
    warehouses?: WarehouseRecord[];
    warehouseLoader?: (keyword: string) => Promise<WarehouseRecord[]>;
  }>(),
  { counterparties: () => [], products: () => [], warehouses: () => [] },
);

const emit = defineEmits<{
  query: [];
  'update:modelValue': [value: DocumentQuery];
}>();

const owners = ref<UserRecord[]>([]);

async function loadOwners(keyword: string) {
  try {
    const result = await listUsersApi({ is_active: true, keyword, page: 1, page_size: 50 });
    owners.value = result.items;
    return owners.value;
  } catch {
    // Owner filtering remains available to roles that may read the user directory.
    return [];
  }
}

function formatOwner(owner: UserRecord) {
  return { label: owner.full_name || owner.email, value: owner.id };
}

function formatCounterparty(counterparty: CounterpartyRecord) {
  return { label: counterparty.name, value: counterparty.id };
}

function formatProduct(product: ProductRecord) {
  return { label: `${product.code} - ${product.name}`, value: product.id };
}

function formatWarehouse(warehouse: WarehouseRecord) {
  return { label: `${warehouse.code} - ${warehouse.name}`, value: warehouse.id };
}

const filters = computed({
  get: () => props.modelValue,
  set: (value: DocumentQuery) => emit('update:modelValue', value),
});

function update(key: keyof DocumentQuery, value: unknown) {
  filters.value = {
    ...filters.value,
    [key]: typeof value === 'string' && value ? value : undefined,
  };
  emit('query');
}

function updateDate(key: 'business_from' | 'business_to', value: string) {
  update(key, value ? new Date(value).toISOString() : undefined);
}

function dateInputValue(value: string | undefined) {
  return value ? value.slice(0, 16) : undefined;
}
</script>

<template>
  <div class="mb-4 flex flex-wrap items-center gap-2">
    <Input
      :value="filters.keyword"
      allow-clear
      class="w-48"
      placeholder="单号、商品或备注"
      @press-enter="emit('query')"
      @update:value="update('keyword', $event)"
    />
    <ErpRemoteSelect
      v-if="counterpartyKey && counterpartyLoader"
      :value="filters[counterpartyKey]"
      allow-clear
      class="w-44"
      :format-option="formatCounterparty"
      :load="counterpartyLoader"
      :placeholder="counterpartyLabel"
      @update:value="update(counterpartyKey, $event)"
    />
    <Select
      v-else-if="counterpartyKey"
      :value="filters[counterpartyKey]"
      allow-clear
      class="w-44"
      :options="counterparties.map((item) => ({ label: item.name, value: item.id }))"
      :placeholder="counterpartyLabel"
      show-search
      @update:value="update(counterpartyKey, $event)"
    />
    <ErpRemoteSelect
      v-if="productLoader"
      :value="filters.product_id"
      allow-clear
      class="w-52"
      :format-option="formatProduct"
      :load="productLoader"
      placeholder="商品"
      @update:value="update('product_id', $event)"
    />
    <Select
      v-else-if="products.length"
      :value="filters.product_id"
      allow-clear
      class="w-52"
      :options="products.map((item) => ({ label: `${item.code} - ${item.name}`, value: item.id }))"
      placeholder="商品"
      show-search
      @update:value="update('product_id', $event)"
    />
    <ErpRemoteSelect
      v-if="warehouseLoader"
      :value="filters.warehouse_id"
      allow-clear
      class="w-48"
      :format-option="formatWarehouse"
      :load="warehouseLoader"
      placeholder="仓库"
      @update:value="update('warehouse_id', $event)"
    />
    <Select
      v-else-if="warehouses.length"
      :value="filters.warehouse_id"
      allow-clear
      class="w-48"
      :options="warehouses.map((item) => ({ label: `${item.code} - ${item.name}`, value: item.id }))"
      placeholder="仓库"
      show-search
      @update:value="update('warehouse_id', $event)"
    />
    <Select
      :value="filters.status"
      allow-clear
      class="w-28"
      :options="[
        { label: '草稿', value: 'draft' },
        { label: '已审核', value: 'approved' },
      ]"
      placeholder="状态"
      @update:value="update('status', $event)"
    />
    <template v-if="showFulfillmentStatus">
      <Select
        :value="filters.receipt_status"
        allow-clear
        class="w-32"
        :options="[
          { label: '未入库', value: 'none' },
          { label: '部分入库', value: 'partial' },
          { label: '全部入库', value: 'completed' },
        ]"
        placeholder="入库状态"
        @update:value="update('receipt_status', $event)"
      />
      <Select
        :value="filters.return_status"
        allow-clear
        class="w-32"
        :options="[
          { label: '未退货', value: 'none' },
          { label: '部分退货', value: 'partial' },
          { label: '全部退货', value: 'completed' },
        ]"
        placeholder="退货状态"
        @update:value="update('return_status', $event)"
      />
    </template>
    <Input
      :value="filters.remark"
      allow-clear
      class="w-40"
      placeholder="备注"
      @press-enter="emit('query')"
      @update:value="update('remark', $event)"
    />
    <ErpRemoteSelect
      :value="filters.owner_id"
      allow-clear
      class="w-44"
      :format-option="formatOwner"
      :load="loadOwners"
      placeholder="制单人"
      @update:value="update('owner_id', $event)"
    />
    <input
      :value="dateInputValue(filters.business_from)"
      aria-label="业务开始时间"
      class="h-8 w-44 rounded border border-[var(--vben-border-color)] bg-transparent px-2 text-sm"
      type="datetime-local"
      @change="updateDate('business_from', ($event.target as HTMLInputElement).value)"
    />
    <input
      :value="dateInputValue(filters.business_to)"
      aria-label="业务结束时间"
      class="h-8 w-44 rounded border border-[var(--vben-border-color)] bg-transparent px-2 text-sm"
      type="datetime-local"
      @change="updateDate('business_to', ($event.target as HTMLInputElement).value)"
    />
  </div>
</template>
