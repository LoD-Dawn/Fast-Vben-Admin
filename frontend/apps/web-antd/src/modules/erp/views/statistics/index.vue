<script lang="ts" setup>
import type {
  StatisticsSummaryRecord,
  StatisticsTimeSeriesRecord,
} from '#/modules/erp/api/erp';

import { onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';

import { Col, Row, Spin } from 'ant-design-vue';

import {
  getStatisticsSummaryApi,
  getStatisticsTimeSeriesApi,
} from '#/modules/erp/api/erp';

import SummaryCard from './modules/summary-card.vue';
import TimeSummaryChart from './modules/time-summary-chart.vue';

defineOptions({ name: 'ErpHome' });

const loading = ref(false);
const summary = ref<StatisticsSummaryRecord>();
const saleTimeSeries = ref<StatisticsTimeSeriesRecord>();
const purchaseTimeSeries = ref<StatisticsTimeSeriesRecord>();

function formatDate(value: Date) {
  return value.toISOString().slice(0, 10);
}

async function loadStatistics() {
  loading.value = true;
  const end = new Date();
  const start = new Date(end);
  start.setDate(end.getDate() - 29);

  try {
    const [summaryResult, saleResult, purchaseResult] = await Promise.all([
      getStatisticsSummaryApi(),
      getStatisticsTimeSeriesApi({
        end: formatDate(end),
        granularity: 'day',
        start: formatDate(start),
        type: 'sale',
      }),
      getStatisticsTimeSeriesApi({
        end: formatDate(end),
        granularity: 'day',
        start: formatDate(start),
        type: 'purchase',
      }),
    ]);

    summary.value = summaryResult;
    saleTimeSeries.value = saleResult;
    purchaseTimeSeries.value = purchaseResult;
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  void loadStatistics();
});
</script>

<template>
  <Page>
    <Spin :spinning="loading">
      <div class="flex flex-col gap-4">
        <SummaryCard :summary="summary" />

        <Row :gutter="16">
          <Col :md="12" :sm="12" :xs="24">
            <TimeSummaryChart
              :data="saleTimeSeries?.items"
              title="销售统计"
            />
          </Col>
          <Col :md="12" :sm="12" :xs="24">
            <TimeSummaryChart
              :data="purchaseTimeSeries?.items"
              title="采购统计"
            />
          </Col>
        </Row>
      </div>
    </Spin>
  </Page>
</template>
