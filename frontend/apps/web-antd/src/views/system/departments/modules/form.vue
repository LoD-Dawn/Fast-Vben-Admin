<script lang="ts" setup>
import type {
  DepartmentCreatePayload,
  DepartmentRecord,
  DepartmentUpdatePayload,
} from '#/api';

import { computed, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';

import { Button } from 'ant-design-vue';

import { createDepartmentApi, updateDepartmentApi } from '#/api';

import { useVbenForm } from '#/adapter/form';

import { generateDepartmentCode, useFormSchema } from '../data';

const emits = defineEmits<{ success: [] }>();

const formData = ref<DepartmentRecord>();

const getTitle = computed(() =>
  formData.value?.id ? '编辑部门' : '新增部门',
);

const [Form, formApi] = useVbenForm({
  layout: 'vertical',
  schema: useFormSchema(),
  showDefaultActions: false,
});

function resetForm() {
  formApi.resetForm();
  formApi.setValues(formData.value || {});
}

const [Modal, modalApi] = useVbenModal({
  async onConfirm() {
    const { valid } = await formApi.validate();
    if (!valid) return;

    const values = await formApi.getValues();
    const payload = {
      is_active: values.is_active ?? true,
      name: values.name,
      parent_id: values.parent_id || undefined,
      remark: values.remark || undefined,
      sort: formData.value?.sort ?? 0,
    } as DepartmentCreatePayload;

    if (formData.value?.id) {
      Object.assign(payload, { code: formData.value.code });
    } else {
      Object.assign(payload, { code: generateDepartmentCode(values.name) });
    }

    modalApi.lock();
    try {
      if (formData.value?.id) {
        await updateDepartmentApi(
          formData.value.id,
          payload as DepartmentUpdatePayload,
        );
      } else {
        await createDepartmentApi(payload);
      }
      modalApi.close();
      emits('success');
    } finally {
      modalApi.lock(false);
    }
  },
  onOpenChange(isOpen) {
    if (!isOpen) return;

    const data = modalApi.getData<DepartmentRecord>();
    formData.value = data;
    formApi.resetForm();

    if (data) {
      formApi.setValues({
        ...data,
        parent_id: data.parent_id || undefined,
        remark: data.remark || undefined,
      });
    }
  },
});
</script>

<template>
  <Modal :title="getTitle">
    <Form class="mx-4" />
    <template #prepend-footer>
      <div class="flex-auto">
        <Button type="primary" danger @click="resetForm">重置</Button>
      </div>
    </template>
  </Modal>
</template>
