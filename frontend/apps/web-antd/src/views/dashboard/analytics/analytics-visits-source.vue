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

  return items.filter((item) => item.value >= 0);
});

function renderChart() {
  renderEcharts({
    legend: {
      bottom: '2%',
      left: 'center',
    },
    series: [
      {
        animationDelay() {
          return Math.random() * 100;
        },
        animationEasing: 'exponentialInOut',
        animationType: 'scale',
        avoidLabelOverlap: false,
        color: ['#5ab1ef', '#b6a2de', '#67e0e3', '#2ec7c9'],
        data: chartData.value,
        emphasis: {
          label: {
            fontSize: '12',
            fontWeight: 'bold',
            show: true,
          },
        },
        itemStyle: {
          borderRadius: 10,
          borderWidth: 2,
        },
        label: {
          position: 'center',
          show: false,
        },
        labelLine: {
          show: false,
        },
        name: '访问来源',
        radius: ['40%', '65%'],
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
