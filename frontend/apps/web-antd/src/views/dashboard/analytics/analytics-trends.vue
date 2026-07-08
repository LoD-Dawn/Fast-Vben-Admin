<script lang="ts" setup>
import type { EchartsUIType } from '@vben/plugins/echarts';

import type { DashboardHourlyTrend } from '#/api';

import { computed, onMounted, ref, watch } from 'vue';

import { EchartsUI, useEcharts } from '@vben/plugins/echarts';

const props = withDefaults(
  defineProps<{
    data?: DashboardHourlyTrend[];
  }>(),
  {
    data: () => [],
  },
);

const chartRef = ref<EchartsUIType>();
const { renderEcharts } = useEcharts(chartRef);

const chartData = computed(() => {
  const trends = props.data.length
    ? props.data
    : Array.from({ length: 18 }, (_, index) => ({
        hour: `${index + 6}:00`,
        login_count: 0,
        operation_count: 0,
      }));

  const loginSeries = trends.map((item) => item.login_count);
  const operationSeries = trends.map((item) => item.operation_count);
  const maxValue = Math.max(...loginSeries, ...operationSeries, 10);
  const yMax = Math.ceil(maxValue / 4) * 4 || 10;

  return {
    hours: trends.map((item) => item.hour),
    loginSeries,
    operationSeries,
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
        areaStyle: {},
        data: chartData.value.loginSeries,
        itemStyle: {
          color: '#5ab1ef',
        },
        smooth: true,
        type: 'line',
      },
      {
        areaStyle: {},
        data: chartData.value.operationSeries,
        itemStyle: {
          color: '#019680',
        },
        smooth: true,
        type: 'line',
      },
    ],
    tooltip: {
      axisPointer: {
        lineStyle: {
          color: '#019680',
          width: 1,
        },
      },
      trigger: 'axis',
    },
    xAxis: {
      axisTick: {
        show: false,
      },
      boundaryGap: false,
      data: chartData.value.hours,
      splitLine: {
        lineStyle: {
          type: 'solid',
          width: 1,
        },
        show: true,
      },
      type: 'category',
    },
    yAxis: [
      {
        axisTick: {
          show: false,
        },
        max: chartData.value.yMax,
        splitArea: {
          show: true,
        },
        splitNumber: 4,
        type: 'value',
      },
    ],
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
