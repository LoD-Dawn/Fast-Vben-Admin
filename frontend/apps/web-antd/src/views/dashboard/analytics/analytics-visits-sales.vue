<script lang="ts" setup>
import type { EchartsUIType } from '@vben/plugins/echarts';

import type { DashboardNamedValue } from '#/api';

import { computed, onMounted, ref, watch } from 'vue';

import { EchartsUI, useEcharts } from '@vben/plugins/echarts';

const props = withDefaults(
  defineProps<{
    data?: DashboardNamedValue[];
  }>(),
  {
    data: () => [],
  },
);

const chartRef = ref<EchartsUIType>();
const { renderEcharts } = useEcharts(chartRef);

const chartData = computed(() => {
  const items = props.data.length
    ? props.data
    : [{ name: '暂无数据', value: 0 }];

  return [...items]
    .filter((item) => item.value >= 0)
    .toSorted((a, b) => a.value - b.value);
});

function renderChart() {
  renderEcharts({
    series: [
      {
        animationDelay() {
          return Math.random() * 400;
        },
        animationEasing: 'exponentialInOut',
        animationType: 'scale',
        center: ['50%', '50%'],
        color: ['#5ab1ef', '#b6a2de', '#67e0e3', '#2ec7c9'],
        data: chartData.value,
        name: '模块分布',
        radius: '80%',
        roseType: 'radius',
        type: 'pie',
      },
    ],
    tooltip: {
      trigger: 'item',
    },
  });
}

onMounted(renderChart);

watch(
  () => props.data,
  () => {
    renderChart();
  },
  { deep: true },
);
</script>

<template>
  <EchartsUI ref="chartRef" />
</template>
