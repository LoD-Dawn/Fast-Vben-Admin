<script lang="ts" setup>
import type { EchartsUIType } from '@vben/plugins/echarts';

import type { StatisticsTimeSeriesRecord } from '#/modules/erp/api/erp';

import { computed, ref, watch } from 'vue';

import { EchartsUI, useEcharts } from '@vben/plugins/echarts';

import { Card } from 'ant-design-vue';

const props = withDefaults(
  defineProps<{
    data?: StatisticsTimeSeriesRecord['items'];
    title: string;
  }>(),
  {
    data: () => [],
  },
);

const chartRef = ref<EchartsUIType>();
const { renderEcharts } = useEcharts(chartRef);

const lineChartOptions: echarts.EChartsOption = {
  grid: {
    bottom: 20,
    containLabel: true,
    left: 20,
    right: 20,
    top: 80,
  },
  legend: {
    top: 50,
  },
  series: [
    {
      areaStyle: {},
      data: [],
      name: '金额',
      smooth: true,
      type: 'line',
    },
  ],
  toolbox: {
    feature: {
      brush: {
        type: ['lineX', 'clear'],
      },
      dataZoom: {
        yAxisIndex: false,
      },
      saveAsImage: {
        name: props.title,
        show: true,
      },
    },
  },
  tooltip: {
    axisPointer: {
      type: 'cross',
    },
    padding: [5, 10],
    trigger: 'axis',
  },
  xAxis: {
    axisTick: {
      show: false,
    },
    boundaryGap: false,
    data: [],
    type: 'category',
  },
  yAxis: {
    axisTick: {
      show: false,
    },
  },
};

const chartData = computed(() => ({
  amounts: props.data.map((item) => Number(item.amount)),
  periods: props.data.map((item) => item.period_start.slice(0, 10)),
}));

watch(
  chartData,
  (value) => {
    renderEcharts({
      ...lineChartOptions,
      series: [
        {
          ...(lineChartOptions.series as any)[0],
          data: value.amounts,
        },
      ],
      xAxis: {
        ...lineChartOptions.xAxis,
        data: value.periods,
      },
    });
  },
  { immediate: true },
);
</script>

<template>
  <Card :title="title">
    <EchartsUI ref="chartRef" />
  </Card>
</template>
