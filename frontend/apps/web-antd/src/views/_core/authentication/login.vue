<script lang="ts" setup>
import type { VbenFormSchema } from '@vben/common-ui';
import type { Recordable } from '@vben/types';

import { computed, onMounted, ref } from 'vue';

import { AuthenticationLogin, z } from '@vben/common-ui';
import { $t } from '@vben/locales';
import { Button, message } from 'ant-design-vue';

import { getEnterpriseOidcStatusApi, getLoginCaptchaApi } from '#/api';
import { useAuthStore } from '#/store';

defineOptions({ name: 'Login' });

const authStore = useAuthStore();
const captchaId = ref('');
const captchaChallenge = ref('');
const showCaptcha = ref(false);
const showMfa = ref(false);
const enterpriseOidcLoginUrl = ref<string>();

const formSchema = computed((): VbenFormSchema[] => {
  const schemas: VbenFormSchema[] = [
    {
      component: 'VbenInput',
      componentProps: {
        autocomplete: 'username',
        placeholder: 'admin@example.com',
      },
      fieldName: 'username',
      label: '邮箱',
      rules: z
        .string()
        .min(1, { message: '请输入邮箱' })
        .email($t('authentication.emailValidErrorTip')),
    },
    {
      component: 'VbenInputPassword',
      componentProps: {
        autocomplete: 'current-password',
        placeholder: $t('authentication.password'),
      },
      fieldName: 'password',
      label: $t('authentication.password'),
      rules: z.string().min(1, { message: $t('authentication.passwordTip') }),
    },
  ];
  if (showCaptcha.value) {
    schemas.push({
      component: 'VbenInput',
      componentProps: {
        placeholder: `请输入结果：${captchaChallenge.value}`,
      },
      fieldName: 'captcha_code',
      label: `验证码（${captchaChallenge.value}）`,
      rules: z.string().min(1, { message: '请输入验证码结果' }),
    });
  }
  if (showMfa.value) {
    schemas.push({
      component: 'VbenInput',
      componentProps: {
        autocomplete: 'one-time-code',
        maxlength: 32,
        placeholder: '输入 6 位验证码或恢复码',
      },
      fieldName: 'mfa_code',
      label: 'MFA 验证码',
      rules: z
        .string()
        .min(6, { message: '请输入 6 位 MFA 验证码或恢复码' }),
    });
  }
  return schemas;
});

async function loadCaptcha(username: string) {
  const captcha = await getLoginCaptchaApi(username);
  captchaId.value = captcha.captcha_id;
  captchaChallenge.value = captcha.challenge_text;
  showCaptcha.value = true;
}

async function handleSubmit(values: Recordable<any>) {
  try {
    await authStore.authLogin({
      ...values,
      captcha_id: showCaptcha.value ? captchaId.value : undefined,
    });
  } catch (error: any) {
    const responseData = error?.response?.data ?? {};
    const errorCode = responseData?.code;
    const username = String(values.username || '');
    if (
      username &&
      (errorCode === 'AUTH_CAPTCHA_REQUIRED' ||
        errorCode === 'AUTH_CAPTCHA_INVALID')
    ) {
      await loadCaptcha(username);
      if (errorCode === 'AUTH_CAPTCHA_INVALID') {
        message.warning('验证码错误或已过期，请重新输入');
      }
    }
    if (errorCode === 'AUTH_MFA_REQUIRED' || errorCode === 'AUTH_MFA_INVALID') {
      showMfa.value = true;
      if (errorCode === 'AUTH_MFA_INVALID') {
        message.warning('MFA 验证码无效，请重试');
      }
    }
    throw error;
  }
}

async function startEnterpriseOidcLogin() {
  if (enterpriseOidcLoginUrl.value) {
    window.location.assign(enterpriseOidcLoginUrl.value);
  }
}

onMounted(async () => {
  const hashQuery = window.location.hash.split('?', 2)[1] || '';
  const ticket =
    new URLSearchParams(window.location.search).get('enterprise_ticket') ||
    new URLSearchParams(hashQuery).get('enterprise_ticket');
  if (ticket) {
    const routeHash = window.location.hash.split('?', 1)[0];
    window.history.replaceState(
      {},
      document.title,
      `${window.location.pathname}${routeHash}`,
    );
    try {
      await authStore.authEnterpriseOidcLogin(ticket);
      return;
    } catch {
      message.error('企业单点登录已失效，请重新发起登录');
    }
  }
  try {
    const status = await getEnterpriseOidcStatusApi();
    enterpriseOidcLoginUrl.value = status.enabled
      ? status.login_url || undefined
      : undefined;
  } catch {
    enterpriseOidcLoginUrl.value = undefined;
  }
});
</script>

<template>
  <AuthenticationLogin
    :form-schema="formSchema"
    :loading="authStore.loginLoading"
    :show-code-login="false"
    :show-qrcode-login="false"
    :show-register="false"
    :show-third-party-login="false"
    sub-title="使用超级管理员或已创建用户账号登录"
    title="Fast Vben Admin"
    @submit="handleSubmit"
  >
    <template #third-party-login>
      <Button
        v-if="enterpriseOidcLoginUrl"
        class="mt-3"
        block
        type="link"
        @click="startEnterpriseOidcLogin"
      >
        企业单点登录
      </Button>
    </template>
  </AuthenticationLogin>
</template>
