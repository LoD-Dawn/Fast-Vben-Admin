<script lang="ts" setup>
import type { EchartsUIType } from '@vben/plugins/echarts';

import type { DashboardRadarSeries } from '#/api';

import { computed, onMounted, ref, watch } from 'vue';

import { EchartsUI, useEcharts } from '@vben/plugins/echarts';

const props = withDefaults(
  defineProps<{
    data?: DashboardRadarSeries[];
  }>(),
  {
    data: () => [],
  },
);

const chartRef = ref<EchartsUIType>();
const { renderEcharts } = useEcharts(chartRef);

const DEVICE_CATEGORIES = ['网页', '移动端', 'Ipad', '客户端', '第三方', '其它'];
const SERIES_COLORS = ['#b6a2de', '#5ab1ef'];

const chartData = computed(() => {
  const series = props.data.length
    ? props.data
    : [
        { name: '访问', values: Array.from({ length: 6 }, () => 0) },
        { name: '趋势', values: Array.from({ length: 6 }, () => 0) },
      ];

  const maxValue = Math.max(
    ...series.flatMap((item) => item.values),
    1,
  );

  return {
    maxValue,
    series,
  };
});

function renderChart() {
  renderEcharts({
    legend: {
      bottom: 0,
      data: chartData.value.series.map((item) => item.name),
    },
    radar: {
      indicator: DEVICE_CATEGORIES.map((name) => ({
        max: chartData.value.maxValue,
        name,
      })),
      radius: '60%',
      splitNumber: 8,
    },
    series: [
      {
        areaStyle: {
          opacity: 1,
          shadowBlur: 0,
          shadowColor: 'rgba(0,0,0,.2)',
          shadowOffsetX: 0,
          shadowOffsetY: 10,
        },
        data: chartData.value.series.map((item, index) => ({
          itemStyle: {
            color: SERIES_COLORS[index % SERIES_COLORS.length],
          },
          name: item.name,
          value: item.values,
        })),
        itemStyle: {
          borderRadius: 10,
          borderWidth: 2,
        },
        symbolSize: 0,
        type: 'radar',
      },
    ],
    tooltip: {},
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
