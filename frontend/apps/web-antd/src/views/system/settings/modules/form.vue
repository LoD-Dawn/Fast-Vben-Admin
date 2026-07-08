<script lang="ts" setup>
import type { SystemSettingRecord } from '#/api';

import { computed, ref } from 'vue';

import { useVbenDrawer } from '@vben/common-ui';

import { updateSettingApi } from '#/api';

import { useVbenForm } from '#/adapter/form';

import { useFormSchema } from '../data';

const emits = defineEmits<{ success: [] }>();

const settingKey = ref<string>();
const isSystem = ref(false);

const [Form, formApi] = useVbenForm({
  schema: useFormSchema(false),
  showDefaultActions: false,
});

const [Drawer, drawerApi] = useVbenDrawer({
  async onConfirm() {
    const { valid } = await formApi.validate();
    if (!valid || !settingKey.value) return;

    const values = await formApi.getValues();
    drawerApi.lock();
    try {
      await updateSettingApi(settingKey.value, {
        description: values.description || undefined,
        group: values.group,
        is_public: values.is_public,
        is_system: values.is_system,
        name: values.name,
        value: values.value,
        value_type: values.value_type,
      });
      emits('success');
      drawerApi.close();
    } catch {
      drawerApi.unlock();
    }
  },
  onOpenChange(isOpen) {
    if (!isOpen) return;

    const data = drawerApi.getData<SystemSettingRecord>();
    formApi.resetForm();
    settingKey.value = data?.key;
    isSystem.value = !!data?.is_system;
    formApi.setState({
      schema: useFormSchema(!!data?.is_system),
    });
    if (data) {
      formApi.setValues(data);
    }
  },
});

const drawerTitle = computed(() =>
  settingKey.value ? `编辑参数 - ${settingKey.value}` : '编辑参数',
);
</script>

<template>
  <Drawer :title="drawerTitle" class="w-[640px]">
    <Form />
  </Drawer>
</template>
