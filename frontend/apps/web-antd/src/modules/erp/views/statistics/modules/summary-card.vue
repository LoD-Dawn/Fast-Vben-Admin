<script lang="ts" setup>
import type { AnalysisOverviewItem } from '@vben/common-ui';

import type { StatisticsSummaryRecord } from '#/modules/erp/api/erp';

import { computed } from 'vue';

import { AnalysisOverview } from '@vben/common-ui';
import {
  SvgBellIcon,
  SvgCakeIcon,
  SvgCardIcon,
  SvgDownloadIcon,
} from '@vben/icons';

const props = defineProps<{
  summary?: StatisticsSummaryRecord;
}>();

const overviewItems = computed<AnalysisOverviewItem[]>(() => {
  const summary = props.summary;

  return [
    {
      icon: SvgCardIcon,
      title: '今日销售额',
      totalTitle: '今日采购额',
      totalValue: Number(summary?.today.purchase_amount ?? 0),
      value: Number(summary?.today.sale_amount ?? 0),
    },
    {
      icon: SvgCakeIcon,
      title: '昨日销售额',
      totalTitle: '昨日采购额',
      totalValue: Number(summary?.yesterday.purchase_amount ?? 0),
      value: Number(summary?.yesterday.sale_amount ?? 0),
    },
    {
      icon: SvgDownloadIcon,
      title: '本月销售额',
      totalTitle: '本月采购额',
      totalValue: Number(summary?.month.purchase_amount ?? 0),
      value: Number(summary?.month.sale_amount ?? 0),
    },
    {
      icon: SvgBellIcon,
      title: '本年销售额',
      totalTitle: '本年采购额',
      totalValue: Number(summary?.year.purchase_amount ?? 0),
      value: Number(summary?.year.sale_amount ?? 0),
    },
  ];
});
</script>

<template>
  <AnalysisOverview :items="overviewItems" />
</template>
