<script setup lang="ts">
import type { VerificationProps } from './typing';

import { ref } from 'vue';

import VerifySlide from './verify-slide.vue';

import './verify.css';

defineOptions({ name: 'Verification' });

const props = withDefaults(defineProps<VerificationProps>(), {
  barSize: () => ({ height: '42px', width: '400px' }),
  captchaType: 'blockPuzzle',
  explain: '',
  imgSize: () => ({ height: '200px', width: '400px' }),
  mode: 'fixed',
});

const emit = defineEmits<{
  onClose: [];
  onError: [unknown];
  onReady: [unknown];
  onSuccess: [data: { captchaVerification: string }];
}>();

const showBox = ref(false);
const slideRef = ref<InstanceType<typeof VerifySlide>>();

function show() {
  showBox.value = true;
  slideRef.value?.refresh();
}

function onClose() {
  showBox.value = false;
  emit('onClose');
}

function onSuccess(data: { captchaVerification: string }) {
  emit('onSuccess', data);
}

defineExpose({ onClose, show, refresh: () => slideRef.value?.refresh() });
</script>

<template>
  <div v-if="showBox" class="verify-mask" @click.self="onClose">
    <div class="verifybox" role="dialog" aria-label="安全验证">
      <div class="verifybox-top">
        滑动验证
        <span class="verifybox-close" aria-label="关闭" @click="onClose">×</span>
      </div>
      <div class="verifybox-bottom">
        <VerifySlide
          ref="slideRef"
          :bar-size="props.barSize"
          :captcha-type="props.captchaType"
          :check-captcha-api="props.checkCaptchaApi"
          :explain="props.explain"
          :get-captcha-api="props.getCaptchaApi"
          :img-size="props.imgSize"
          @on-error="(error) => emit('onError', error)"
          @on-ready="(ready) => emit('onReady', ready)"
          @on-success="onSuccess"
        />
      </div>
    </div>
  </div>
</template>
