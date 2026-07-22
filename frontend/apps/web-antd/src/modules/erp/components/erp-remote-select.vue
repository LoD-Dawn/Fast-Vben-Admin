<script lang="ts" setup>
import { computed, onBeforeUnmount, ref } from 'vue';

import { Select } from 'ant-design-vue';

const props = withDefaults(
  defineProps<{
    allowClear?: boolean;
    class?: string;
    disabled?: boolean;
    formatOption: (record: any) => { label: string; value: string };
    load: (keyword: string) => Promise<any[]>;
    mode?: 'multiple' | 'tags';
    placeholder?: string;
    value?: string | string[];
  }>(),
  { allowClear: false, disabled: false, mode: undefined, placeholder: undefined, value: undefined },
);

const emit = defineEmits<{
  change: [value: string | string[] | undefined];
  'update:value': [value: string | string[] | undefined];
}>();

const loading = ref(false);
const options = ref<Array<{ label: string; value: string }>>([]);
let searchTimer: number | undefined;

const selectValue = computed({
  get: () => props.value,
  set: (value) => {
    emit('update:value', value);
    emit('change', value);
  },
});

async function loadOptions(keyword = '') {
  loading.value = true;
  try {
    const records = await props.load(keyword);
    // Make options visible only after the loading state settles; otherwise an
    // option can unmount between pointer down and the Select's click handler.
    loading.value = false;
    options.value = records.map(props.formatOption);
  } catch {
    options.value = [];
    loading.value = false;
  }
}

function search(keyword: string) {
  if (searchTimer) window.clearTimeout(searchTimer);
  searchTimer = window.setTimeout(() => void loadOptions(keyword), 250);
}

function dropdownVisibleChange(open: boolean) {
  if (open && options.value.length === 0) void loadOptions();
}

onBeforeUnmount(() => {
  if (searchTimer) window.clearTimeout(searchTimer);
});
</script>

<template>
  <Select
    v-model:value="selectValue"
    :allow-clear="allowClear"
    :class="$props.class"
    :disabled="disabled"
    :filter-option="false"
    :loading="loading"
    :mode="mode"
    :options="options"
    :placeholder="placeholder"
    show-search
    @dropdown-visible-change="dropdownVisibleChange"
    @search="search"
  />
</template>
