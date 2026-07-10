<script lang="ts" setup>
import type { UserCreatePayload, UserRecord, UserUpdatePayload } from '#/api';

import { computed, ref } from 'vue';

import { useVbenDrawer } from '@vben/common-ui';

import {
  createUserApi,
  getUserPostsApi,
  getUserRolesApi,
  updateUserApi,
  updateUserPostsApi,
  updateUserRolesApi,
} from '#/api';

import { useVbenForm } from '#/adapter/form';

import { useFormSchema } from '../data';

const emits = defineEmits<{ success: [] }>();

const formData = ref<UserRecord>();
const userId = ref<string>();

const [Form, formApi] = useVbenForm({
  schema: useFormSchema(false),
  showDefaultActions: false,
});

const [Drawer, drawerApi] = useVbenDrawer({
  async onConfirm() {
    const { valid } = await formApi.validate();
    if (!valid) return;

    const values = await formApi.getValues();
    const {
      password,
      post_ids: postIds = [],
      role_ids: roleIds = [],
      ...payload
    } = values;
    const userPayload = payload as UserCreatePayload;

    if (!userId.value && !password) {
      return;
    }

    drawerApi.lock();
    try {
      if (userId.value) {
        await updateUserApi(userId.value, {
          ...userPayload,
          ...(password ? { password } : {}),
        } as UserUpdatePayload);
        await updateUserRolesApi(userId.value, { role_ids: roleIds });
        await updateUserPostsApi(userId.value, { post_ids: postIds });
      } else {
        const user = await createUserApi({
          ...userPayload,
          password,
        });
        if (roleIds.length > 0) {
          await updateUserRolesApi(user.id, { role_ids: roleIds });
        }
        if (postIds.length > 0) {
          await updateUserPostsApi(user.id, { post_ids: postIds });
        }
      }
      emits('success');
      drawerApi.close();
    } catch {
      drawerApi.unlock();
    }
  },
  async onOpenChange(isOpen) {
    if (!isOpen) return;

    const data = drawerApi.getData<UserRecord>();
    formApi.resetForm();
    formData.value = data;
    userId.value = data?.id;
    formApi.setState({
      schema: useFormSchema(!!data?.id),
    });

    if (data?.id) {
      const [userRoles, userPosts] = await Promise.all([
        getUserRolesApi(data.id),
        getUserPostsApi(data.id),
      ]);
      formApi.setValues({
        ...data,
        department_id: data.department_id || undefined,
        password: '',
        post_ids: userPosts.map((post) => post.id),
        role_ids: userRoles.map((role) => role.id),
      });
    }
  },
});

const drawerTitle = computed(() =>
  userId.value ? '编辑用户' : '新增用户',
);
</script>

<template>
  <Drawer :title="drawerTitle">
    <Form />
  </Drawer>
</template>
