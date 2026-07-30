/**
 * Type Definitions for Server Status
 *
 * The `getChart()` window accessor and the `HistoricalDataResponse` shape that
 * used to live here were removed on 2026-07-30 together with the Chart.js
 * modules that consumed them: this page no longer loads any chart library. See
 * ./series-client.ts for the payload types the inline-SVG renderer uses.
 */

export interface ServerMetrics {
  timestamp: number;
  cpu_percent: number | null;
  memory_percent: number | null;
  disk_percent: number | null;
  gpu_percent: number | null;
  disk_read_mb_total: number;
  disk_write_mb_total: number;
  net_sent_mb_total: number;
  net_recv_mb_total: number;
  visitor_pool_allocated: number | null;
  visitor_pool_total: number | null;
  active_users_count: number | null;
}
