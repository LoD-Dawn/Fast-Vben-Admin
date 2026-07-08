<script lang="ts" setup>
import type { MenuCreatePayload, MenuRecord, MenuUpdatePayload } from '#/api';

import { computed, ref } from 'vue';

import { useVbenDrawer } from '@vben/common-ui';

import { createMenuApi, updateMenuApi } from '#/api';

import { useVbenForm } from '#/adapter/form';

import { useFormSchema } from '../data';

const emits = defineEmits<{ success: [] }>();

const formData = ref<MenuRecord>();
const menuId = ref<string>();

const [Form, formApi] = useVbenForm({
  schema: useFormSchema(),
  showDefaultActions: false,
});

const [Drawer, drawerApi] = useVbenDrawer({
  async onConfirm() {
    const { valid } = await formApi.validate();
    if (!valid) return;

    const values = await formApi.getValues();
    const payload = {
      ...values,
      component: values.component || undefined,
      icon: values.icon || undefined,
      parent_id: values.parent_id || undefined,
      permission_code: values.permission_code || undefined,
      route_name: values.route_name || undefined,
      route_path: values.route_path || undefined,
    } as MenuCreatePayload;

    drawerApi.lock();
    try {
      if (menuId.value) {
        await updateMenuApi(menuId.value, payload as MenuUpdatePayload);
      } else {
        await createMenuApi(payload);
      }
      emits('success');
      drawerApi.close();
    } catch {
      drawerApi.unlock();
    }
  },
  onOpenChange(isOpen) {
    if (!isOpen) return;

    const data = drawerApi.getData<MenuRecord>();
    formApi.resetForm();
    formData.value = data;
    menuId.value = data?.id;

    if (data) {
      formApi.setValues({
        ...data,
        parent_id: data.parent_id || undefined,
      });
    }
  },
});

const drawerTitle = computed(() =>
  menuId.value ? '编辑菜单' : '新增菜单',
);
</script>

<template>
  <Drawer :title="drawerTitle" class="w-[720px]">
    <Form />
  </Drawer>
</template>
