<script lang="ts" setup>
import type { DictionaryItemCreatePayload, DictionaryItemRecord } from '#/api';

import { computed, ref } from 'vue';

import { useVbenDrawer } from '@vben/common-ui';

import { createDictionaryItemApi, updateDictionaryItemApi } from '#/api';

import { useVbenForm } from '#/adapter/form';

import { useItemFormSchema } from '../data';

const emits = defineEmits<{ success: [] }>();

const itemId = ref<string>();
const typeId = ref<string>();

const [Form, formApi] = useVbenForm({
  schema: useItemFormSchema(),
  showDefaultActions: false,
});

const [Drawer, drawerApi] = useVbenDrawer({
  async onConfirm() {
    const { valid } = await formApi.validate();
    if (!valid || !typeId.value) return;

    const values = await formApi.getValues();
    const payload = {
      ...values,
      color: values.color || undefined,
      extra_data: values.extra_data || undefined,
      type_id: typeId.value,
    } as DictionaryItemCreatePayload;

    drawerApi.lock();
    try {
      if (itemId.value) {
        await updateDictionaryItemApi(itemId.value, payload);
      } else {
        await createDictionaryItemApi(payload);
      }
      emits('success');
      drawerApi.close();
    } catch {
      drawerApi.unlock();
    }
  },
  onOpenChange(isOpen) {
    if (!isOpen) return;

    const data = drawerApi.getData<{
      record?: DictionaryItemRecord;
      typeId: string;
    }>();
    formApi.resetForm();
    typeId.value = data.typeId;
    itemId.value = data.record?.id;
    if (data.record) {
      formApi.setValues(data.record);
    }
  },
});

const drawerTitle = computed(() =>
  itemId.value ? '编辑字典项' : '新增字典项',
);
</script>

<template>
  <Drawer :title="drawerTitle">
    <Form />
  </Drawer>
</template>
