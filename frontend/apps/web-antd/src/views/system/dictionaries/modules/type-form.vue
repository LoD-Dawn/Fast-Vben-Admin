<script lang="ts" setup>
import type { DictionaryTypeCreatePayload, DictionaryTypeRecord } from '#/api';

import { computed, ref } from 'vue';

import { useVbenDrawer } from '@vben/common-ui';

import { createDictionaryTypeApi, updateDictionaryTypeApi } from '#/api';

import { useVbenForm } from '#/adapter/form';

import { useTypeFormSchema } from '../data';

const emits = defineEmits<{ success: [] }>();

const typeId = ref<string>();

const [Form, formApi] = useVbenForm({
  schema: useTypeFormSchema(),
  showDefaultActions: false,
});

const [Drawer, drawerApi] = useVbenDrawer({
  async onConfirm() {
    const { valid } = await formApi.validate();
    if (!valid) return;

    const values = await formApi.getValues();
    drawerApi.lock();
    try {
      if (typeId.value) {
        await updateDictionaryTypeApi(
          typeId.value,
          values as DictionaryTypeCreatePayload,
        );
      } else {
        await createDictionaryTypeApi(values as DictionaryTypeCreatePayload);
      }
      emits('success');
      drawerApi.close();
    } catch {
      drawerApi.unlock();
    }
  },
  onOpenChange(isOpen) {
    if (!isOpen) return;

    const data = drawerApi.getData<DictionaryTypeRecord>();
    formApi.resetForm();
    typeId.value = data?.id;
    if (data) {
      formApi.setValues(data);
    }
  },
});

const drawerTitle = computed(() =>
  typeId.value ? '编辑字典类型' : '新增字典类型',
);
</script>

<template>
  <Drawer :title="drawerTitle">
    <Form />
  </Drawer>
</template>
