<script lang="ts" setup>
import type { AnalysisOverviewItem } from '@vben/common-ui';
import type { TabOption } from '@vben/types';

import type { DashboardAnalytics } from '#/api';

import { computed, onMounted, ref } from 'vue';

import {
  AnalysisChartCard,
  AnalysisChartsTabs,
  AnalysisOverview,
} from '@vben/common-ui';
import {
  SvgBellIcon,
  SvgCakeIcon,
  SvgCardIcon,
  SvgDownloadIcon,
} from '@vben/icons';
import { message } from 'ant-design-vue';

import { getDashboardAnalyticsApi } from '#/api';

import AnalyticsTrends from './analytics-trends.vue';
import AnalyticsVisitsData from './analytics-visits-data.vue';
import AnalyticsVisitsSales from './analytics-visits-sales.vue';
import AnalyticsVisitsSource from './analytics-visits-source.vue';
import AnalyticsVisits from './analytics-visits.vue';

const loading = ref(false);
const analytics = ref<DashboardAnalytics | null>(null);

const overviewItems = computed<AnalysisOverviewItem[]>(() => {
  const overview = analytics.value?.overview;
  if (!overview) {
    return [];
  }

  return [
    {
      icon: SvgCardIcon,
      title: '用户量',
      totalTitle: '总用户量',
      totalValue: overview.user_total,
      value: overview.user_count,
    },
    {
      icon: SvgCakeIcon,
      title: '访问量',
      totalTitle: '总访问量',
      totalValue: overview.login_total,
      value: overview.login_count,
    },
    {
      icon: SvgDownloadIcon,
      title: '下载量',
      totalTitle: '总下载量',
      totalValue: overview.file_total,
      value: overview.file_count,
    },
    {
      icon: SvgBellIcon,
      title: '使用量',
      totalTitle: '总使用量',
      totalValue: overview.operation_total,
      value: overview.operation_count,
    },
  ];
});

const chartTabs: TabOption[] = [
  {
    label: '流量趋势',
    value: 'trends',
  },
  {
    label: '月访问量',
    value: 'visits',
  },
];

async function loadAnalytics() {
  loading.value = true;
  try {
    analytics.value = await getDashboardAnalyticsApi();
  } catch {
    message.error('仪表盘数据加载失败');
  } finally {
    loading.value = false;
  }
}

onMounted(loadAnalytics);
</script>

<template>
  <div class="p-5">
    <AnalysisOverview :items="overviewItems" />
    <AnalysisChartsTabs :tabs="chartTabs" class="mt-5">
      <template #trends>
        <AnalyticsTrends :data="analytics?.hourly_trends ?? []" />
      </template>
      <template #visits>
        <AnalyticsVisits :data="analytics?.monthly_visits ?? []" />
      </template>
    </AnalysisChartsTabs>

    <div class="mt-5 w-full md:flex">
      <AnalysisChartCard class="mt-5 md:mt-0 md:mr-4 md:w-1/3" title="访问数量">
        <AnalyticsVisitsData :data="analytics?.device_radar ?? []" />
      </AnalysisChartCard>
      <AnalysisChartCard class="mt-5 md:mt-0 md:mr-4 md:w-1/3" title="访问来源">
        <AnalyticsVisitsSource :data="analytics?.login_sources ?? []" />
      </AnalysisChartCard>
      <AnalysisChartCard class="mt-5 md:mt-0 md:w-1/3" title="模块分布">
        <AnalyticsVisitsSales :data="analytics?.module_distribution ?? []" />
      </AnalysisChartCard>
    </div>
  </div>
</template>
