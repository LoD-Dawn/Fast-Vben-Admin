<script lang="ts" setup>
import type { EchartsUIType } from '@vben/plugins/echarts';

import type { DashboardMonthlyVisit } from '#/api';

import { computed, onMounted, ref, watch } from 'vue';

import { EchartsUI, useEcharts } from '@vben/plugins/echarts';

const props = withDefaults(
  defineProps<{
    data?: DashboardMonthlyVisit[];
  }>(),
  {
    data: () => [],
  },
);

const chartRef = ref<EchartsUIType>();
const { renderEcharts } = useEcharts(chartRef);

const chartData = computed(() => {
  const visits = props.data.length
    ? props.data
    : Array.from({ length: 12 }, (_, index) => ({
        month: `${index + 1}月`,
        count: 0,
      }));

  const values = visits.map((item) => item.count);
  const maxValue = Math.max(...values, 10);
  const yMax = Math.ceil(maxValue / 4) * 4 || 10;

  return {
    months: visits.map((item) => item.month),
    values,
    yMax,
  };
});

function renderChart() {
  renderEcharts({
    grid: {
      bottom: 0,
      containLabel: true,
      left: '1%',
      right: '1%',
      top: '2 %',
    },
    series: [
      {
        barMaxWidth: 80,
        data: chartData.value.values,
        type: 'bar',
      },
    ],
    tooltip: {
      axisPointer: {
        lineStyle: {
          width: 1,
        },
      },
      trigger: 'axis',
    },
    xAxis: {
      data: chartData.value.months,
      type: 'category',
    },
    yAxis: {
      max: chartData.value.yMax,
      splitNumber: 4,
      type: 'value',
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
