<script lang="ts" setup>
import type { PurchaseOrderRecord } from '#/modules/erp/api/erp';
import type { PurchaseOrderLineForm } from '../data';

import { computed, ref } from 'vue';

import { useVbenDrawer } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';

import { Button, message, Tag } from 'ant-design-vue';

import { useVbenForm } from '#/adapter/form';
import { uploadFileApi } from '#/api';
import DocumentAttachments from '#/modules/erp/components/document-attachments.vue';
import {
  createDocumentAttachmentApi,
  createPurchaseOrderApi,
  getPurchaseOrderApi,
  listSettlementAccountsApi,
  updatePurchaseOrderApi,
} from '#/modules/erp/api/erp';

import { useOrderFormSchema } from '../data';
import PurchaseOrderItemForm from './item-form.vue';

type FormType = 'create' | 'detail' | 'edit';

interface PurchaseOrderDrawerData {
  mode: FormType;
  order?: PurchaseOrderRecord;
  orderId?: string;
}

const emit = defineEmits<{ success: [] }>();
const formType = ref<FormType>('create');
const currentOrder = ref<PurchaseOrderRecord>();
const orderLines = ref<PurchaseOrderLineForm[]>([]);
const discountRate = ref(0);
const itemFormRef = ref<InstanceType<typeof PurchaseOrderItemForm>>();
const pendingAttachments = ref<File[]>([]);
const attachmentInputRef = ref<HTMLInputElement>();
const attachmentsOpen = ref(false);

const title = computed(() => {
  if (formType.value === 'create') return '新增采购订单';
  if (formType.value === 'edit') return '编辑采购订单';
  return '采购订单详情';
});

const [Form, formApi] = useVbenForm({
  commonConfig: {
    componentProps: { class: 'w-full' },
    labelWidth: 120,
  },
  handleValuesChange: (values, changedFields) => {
    if (changedFields.includes('discount_rate')) {
      discountRate.value = Number(values.discount_rate ?? 0);
    }
  },
  layout: 'vertical',
  schema: useOrderFormSchema(formType.value),
  showDefaultActions: false,
  wrapperClass: 'grid-cols-3',
});

function createRowKey(id?: string) {
  return id || crypto.randomUUID();
}

function mapOrderLines(order: PurchaseOrderRecord): PurchaseOrderLineForm[] {
  return (order.items ?? []).map((item) => ({
    id: item.id,
    product_amount: Number(item.product_amount),
    product_barcode: item.product_barcode || undefined,
    product_id: item.product_id,
    product_name: item.product_name,
    quantity: Number(item.quantity),
    received_quantity: Number(item.received_quantity),
    remark: item.remark || undefined,
    returned_quantity: Number(item.returned_quantity),
    row_key: createRowKey(item.id),
    tax_amount: Number(item.tax_amount),
    tax_rate: Number(item.tax_rate),
    total_amount: Number(item.total_amount),
    unit_name: item.unit_name,
    unit_price: Number(item.unit_price),
  }));
}

function nowForForm() {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60_000)
    .toISOString()
    .slice(0, 19);
}

function chooseAttachments() {
  attachmentInputRef.value?.click();
}

function stageAttachments(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (file && file.size > 10 * 1024 * 1024) {
    message.warning('附件大小不能超过 10MB');
  } else {
    pendingAttachments.value = file ? [file] : [];
  }
  if (attachmentInputRef.value) attachmentInputRef.value.value = '';
}

function removePendingAttachment(index: number) {
  pendingAttachments.value.splice(index, 1);
}

async function attachPendingFiles(order: PurchaseOrderRecord) {
  for (let index = 0; index < pendingAttachments.value.length; index += 1) {
    const file = pendingAttachments.value[index];
    if (!file) continue;
    const stored = await uploadFileApi(file);
    await createDocumentAttachmentApi(
      'purchase_order',
      order.id,
      stored.id,
      index,
    );
  }
  pendingAttachments.value = [];
}

function handleUpdateItems(items: PurchaseOrderLineForm[]) {
  orderLines.value = items;
  formApi.setValues({ items });
}

function handleUpdateDiscountAmount(value: number) {
  formApi.setValues({ discount_amount: value });
}

function handleUpdateTotalAmount(value: number) {
  formApi.setValues({ total_amount: value });
}

async function applyOrder(order: PurchaseOrderRecord) {
  currentOrder.value = order;
  orderLines.value = mapOrderLines(order);
  discountRate.value = Number(order.discount_rate ?? 0);
  await formApi.setValues({
    ...order,
    deposit_amount: Number(order.deposit_amount),
    discount_amount: Number(order.discount_amount),
    discount_rate: Number(order.discount_rate),
    items: orderLines.value,
    settlement_account_id: order.settlement_account_id || undefined,
    total_amount: Number(order.total_amount),
  });
}

const [Drawer, drawerApi] = useVbenDrawer({
  async onConfirm() {
    const { valid } = await formApi.validate();
    if (!valid) {
      message.warning('请检查并填写订单必填信息');
      return;
    }

    try {
      const itemFormInstance = Array.isArray(itemFormRef.value)
        ? itemFormRef.value[0]
        : itemFormRef.value;
      if (!itemFormInstance) {
        throw new Error('采购产品清单尚未加载完成');
      }
      itemFormInstance.validate();
    } catch (error) {
      message.error(
        error instanceof Error ? error.message : '采购产品清单校验失败',
      );
      return;
    }

    const values = await formApi.getValues();
    const supplierId = values.supplier_id as string | undefined;
    if (!supplierId) return;

    drawerApi.lock();
    try {
      const payload = {
        business_at: values.business_at || undefined,
        deposit_amount: String(values.deposit_amount ?? 0),
        discount_rate: String(values.discount_rate ?? 0),
        items: orderLines.value.map((item) => ({
          product_id: item.product_id!,
          quantity: String(item.quantity),
          remark: item.remark || undefined,
          tax_rate: String(item.tax_rate ?? 0),
          unit_price: String(item.unit_price),
        })),
        remark: values.remark || undefined,
        settlement_account_id: values.settlement_account_id || undefined,
        supplier_id: supplierId,
      };

      const savedOrder =
        formType.value === 'create'
          ? await createPurchaseOrderApi(payload)
          : await updatePurchaseOrderApi(
              currentOrder.value!.id,
              payload,
              currentOrder.value!.version,
            );
      await attachPendingFiles(savedOrder);
      await drawerApi.close();
      emit('success');
      message.success('操作成功');
    } finally {
      drawerApi.lock(false);
    }
  },
  async onOpenChange(isOpen) {
    if (!isOpen) {
      currentOrder.value = undefined;
      orderLines.value = [];
      pendingAttachments.value = [];
      return;
    }

    const drawerData = drawerApi.getData<PurchaseOrderDrawerData>();
    formType.value = drawerData?.mode ?? 'create';
    currentOrder.value = undefined;
    orderLines.value = [];
    pendingAttachments.value = [];
    discountRate.value = 0;
    await formApi.resetForm();
    formApi.setDisabled(formType.value === 'detail');
    await formApi.updateSchema(useOrderFormSchema(formType.value));

    if (!drawerData?.orderId) {
      const accounts = await listSettlementAccountsApi({
        page: 1,
        page_size: 200,
      });
      const defaultAccount = accounts.items.find((item) => item.is_default);
      await formApi.setValues({
        business_at: nowForForm(),
        deposit_amount: 0,
        discount_rate: 0,
        no: '',
        settlement_account_id: defaultAccount?.id,
      });
      return;
    }

    if (drawerData.order) {
      await applyOrder(drawerData.order);
    }
    drawerApi.lock();
    try {
      await applyOrder(await getPurchaseOrderApi(drawerData.orderId));
    } finally {
      drawerApi.lock(false);
    }
  },
});
</script>

<template>
  <Drawer
    class="w-[min(1280px,calc(100vw-24px))]"
    :show-confirm-button="formType !== 'detail'"
    :title="title"
  >
    <DocumentAttachments
      v-model:open="attachmentsOpen"
      :document-id="currentOrder?.id"
      document-type="purchase_order"
      :readonly="formType === 'detail'"
    />
    <Form class="mx-3">
      <template #attachments>
        <div class="flex min-h-8 flex-wrap items-center gap-2">
          <input
            ref="attachmentInputRef"
            accept=".pdf,.doc,.docx,.xls,.xlsx,.txt,.jpg,.jpeg,.png"
            class="hidden"
            type="file"
            @change="stageAttachments"
          />
          <Button
            v-if="formType !== 'detail'"
            class="gap-1"
            @click="chooseAttachments"
          >
            <IconifyIcon class="size-4" icon="lucide:upload" />
            <span>选择文件</span>
          </Button>
          <Button
            v-if="currentOrder"
            type="link"
            @click="attachmentsOpen = true"
          >
            {{ formType === 'detail' ? '查看附件' : '管理已上传附件' }}
          </Button>
          <Tag
            v-for="(file, index) in pendingAttachments"
            :key="`${file.name}-${index}`"
            :closable="formType !== 'detail'"
            @close="removePendingAttachment(index)"
          >
            {{ file.name }}
          </Tag>
          <span
            v-if="formType === 'detail' && !currentOrder"
            class="text-muted-foreground"
          >
            -
          </span>
        </div>
      </template>
      <template #items>
        <PurchaseOrderItemForm
          ref="itemFormRef"
          :disabled="formType === 'detail'"
          :discount-rate="discountRate"
          :items="orderLines"
          @update:discount-amount="handleUpdateDiscountAmount"
          @update:items="handleUpdateItems"
          @update:total-amount="handleUpdateTotalAmount"
        />
      </template>
    </Form>
  </Drawer>
</template>
