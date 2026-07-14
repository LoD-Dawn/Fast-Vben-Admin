# 监控与告警

## 健康检查

- `GET /api/v1/utils/health-check`：存活探针，仅说明进程可以响应 HTTP 请求。
- `GET /api/v1/utils/health-status`：就绪状态，返回 PostgreSQL 和 Redis 的可用性。数据库不可用时不得把实例放入业务流量；Redis 不可用时服务会降级为不使用缓存。

## Prometheus 指标

`GET /metrics` 输出 Prometheus 文本格式指标，包括：

- `fast_vben_http_requests_total`：按请求方法、路由模板和状态码统计的请求总数。
- `fast_vben_http_request_duration_seconds`：按请求方法和路由模板统计的请求耗时直方图。
- `fast_vben_http_requests_in_progress`：当前处理中的请求数。
- Prometheus 默认进程与 Python 运行时指标。

生产环境必须将 `/metrics` 限制在监控网络内。可同时设置 `METRICS_AUTH_TOKEN`，Prometheus 请求需携带 `Authorization: Bearer <token>`。不要把 Token 写入仓库或公开的抓取配置。

示例抓取配置：

```yaml
scrape_configs:
  - job_name: fast-vben-admin
    metrics_path: /metrics
    static_configs:
      - targets: ['api.internal.example:8000']
    authorization:
      type: Bearer
      credentials: ${FAST_VBEN_METRICS_TOKEN}
```

## 推荐告警规则

```yaml
groups:
  - name: fast-vben-admin
    rules:
      - alert: FastVbenApiErrorRateHigh
        expr: |
          sum(rate(fast_vben_http_requests_total{status_code=~"5.."}[5m]))
          / clamp_min(sum(rate(fast_vben_http_requests_total[5m])), 1) > 0.02
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: API 5xx error rate is above 2%
      - alert: FastVbenApiLatencyHigh
        expr: |
          histogram_quantile(0.95, sum(rate(fast_vben_http_request_duration_seconds_bucket[5m])) by (le)) > 1
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: API p95 latency is above 1 second
      - alert: FastVbenReadinessDown
        expr: probe_success{job="fast-vben-readiness"} == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: API readiness endpoint cannot be reached
```

将告警接入现有的 Alertmanager、企业微信、钉钉或邮件渠道；告警通知中不要包含访问令牌、密码、MFA 密钥或完整用户请求参数。
