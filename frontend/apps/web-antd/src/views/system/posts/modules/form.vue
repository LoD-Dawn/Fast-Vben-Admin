<script lang="ts" setup>
import type { PostCreatePayload, PostRecord, PostUpdatePayload } from '#/api';

import { computed, ref } from 'vue';

import { useVbenDrawer } from '@vben/common-ui';

import { createPostApi, updatePostApi } from '#/api';

import { useVbenForm } from '#/adapter/form';

import { useFormSchema } from '../data';

const emits = defineEmits<{ success: [] }>();

const formData = ref<PostRecord>();
const postId = ref<string>();

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
      code: values.code,
      is_active: values.is_active ?? true,
      name: values.name,
      remark: values.remark || undefined,
      sort: values.sort ?? 0,
    };

    drawerApi.lock();
    try {
      if (postId.value) {
        await updatePostApi(postId.value, payload as PostUpdatePayload);
      } else {
        await createPostApi(payload as PostCreatePayload);
      }
      emits('success');
      drawerApi.close();
    } catch {
      drawerApi.unlock();
    }
  },
  onOpenChange(isOpen) {
    if (!isOpen) return;

    const data = drawerApi.getData<PostRecord>();
    formApi.resetForm();
    formData.value = data;
    postId.value = data?.id;

    if (data) {
      formApi.setValues({
        ...data,
        remark: data.remark || undefined,
      });
    }
  },
});

const drawerTitle = computed(() =>
  postId.value ? '编辑岗位' : '新增岗位',
);
</script>

<template>
  <Drawer :title="drawerTitle" class="w-[560px]">
    <Form />
  </Drawer>
</template>
