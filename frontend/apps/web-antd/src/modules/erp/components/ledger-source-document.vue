<script lang="ts" setup>
import { computed, ref } from 'vue';

import { Eye } from '@vben/icons';
import { Button, Descriptions, Drawer, Empty, Spin, Table, message } from 'ant-design-vue';

import { requestClient } from '#/api/request';

const props = defineProps<{
  documentId: string;
  documentNo: string;
  documentType: string;
}>();

const open = ref(false);
const loading = ref(false);
const document = ref<Record<string, any>>();

const documentPaths: Record<string, string> = {
  purchase_in: 'purchase-ins',
  purchase_return: 'purchase-returns',
  sale_out: 'sale-outs',
  sale_return: 'sale-returns',
  stock_check: 'stock-checks',
  stock_in: 'stock-ins',
  stock_move: 'stock-moves',
  stock_out: 'stock-outs',
};

const title = computed(() => `来源单据 ${props.documentNo}`);
const items = computed(() => document.value?.items ?? []);
const columns = computed(() => [
  { dataIndex: 'line_no', title: '行号', width: 70 },
  { dataIndex: 'product_name', title: '商品', minWidth: 180 },
  { dataIndex: 'warehouse_name', title: '仓库', minWidth: 140 },
  { dataIndex: 'quantity', title: '数量', width: 110 },
]);

async function show() {
  const path = documentPaths[props.documentType];
  if (!path) return;
  loading.value = true;
  document.value = undefined;
  open.value = true;
  try {
    document.value = await requestClient.get<Record<string, any>>(
      `/erp/${path}/${props.documentId}`,
    );
  } catch {
    open.value = false;
    message.warning('无权查看来源单据或单据不存在');
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <Button size="small" type="link" @click="show">
    <Eye class="size-4" />查看来源
  </Button>
  <Drawer v-model:open="open" :title="title" placement="right" width="min(880px, 100vw)">
    <Spin :spinning="loading">
      <template v-if="document">
        <Descriptions bordered :column="2" size="small">
          <Descriptions.Item label="单据编号">{{ document.no }}</Descriptions.Item>
          <Descriptions.Item label="状态">{{ document.status }}</Descriptions.Item>
          <Descriptions.Item label="业务时间">{{ document.business_at }}</Descriptions.Item>
          <Descriptions.Item label="总数量">{{ document.total_quantity }}</Descriptions.Item>
          <Descriptions.Item :span="2" label="备注">{{ document.remark || '-' }}</Descriptions.Item>
        </Descriptions>
        <Table class="mt-4" :columns="columns" :data-source="items" :pagination="false" row-key="id" size="small" />
      </template>
      <Empty v-else-if="!loading" description="未找到来源单据" />
    </Spin>
  </Drawer>
</template>
