/**
 * Metrics Updater Module
 * Updates current metric values displayed on the page (not charts)
 *
 * Charts are pre-rendered by backend - this only updates the numeric values.
 */

import type { ServerMetrics } from "./types";

// State for rate calculations
let lastDiskRead: number | null = null;
let lastDiskWrite: number | null = null;
let lastNetSent: number | null = null;
let lastNetRecv: number | null = null;
let lastTimestamp: number | null = null;
let gpuAvailable: boolean | null = null;

export interface MetricsResult {
  success: boolean;
  sessionExpired?: boolean;
  error?: string;
}

/**
 * Update all metric current values from API
 */
export async function updateMetrics(): Promise<MetricsResult> {
  try {
    const response = await fetch("/api/server-status/");

    // Check for session expiration (redirects to visitor-expired)
    if (response.status === 401 || response.status === 403) {
      console.log("[metrics-updater] Session expired (401/403)");
      return { success: false, sessionExpired: true };
    }

    // Check for redirect to visitor-expired page
    if (response.redirected && response.url.includes("visitor-expired")) {
      console.log("[metrics-updater] Redirected to visitor-expired");
      return { success: false, sessionExpired: true };
    }

    if (!response.ok) {
      console.warn(`[metrics-updater] API returned ${response.status}`);
      return { success: false, error: `HTTP ${response.status}` };
    }

    const data: ServerMetrics = await response.json();
    const timestamp = data.timestamp;

    // Update CPU
    const cpuEl = document.getElementById("cpuCurrentValue");
    if (cpuEl) {
      const cpuValue = data.cpu_percent;
      cpuEl.textContent =
        cpuValue !== null && !isNaN(cpuValue)
          ? cpuValue.toFixed(1) + "%"
          : "N/A";
    }

    // Update Memory
    const memoryEl = document.getElementById("memoryCurrentValue");
    if (memoryEl) {
      const memoryValue = data.memory_percent;
      memoryEl.textContent =
        memoryValue !== null && !isNaN(memoryValue)
          ? memoryValue.toFixed(1) + "%"
          : "N/A";
    }

    // Update Disk
    const diskEl = document.getElementById("diskCurrentValue");
    if (diskEl) {
      const diskValue = data.disk_percent;
      diskEl.textContent =
        diskValue !== null && !isNaN(diskValue)
          ? diskValue.toFixed(1) + "%"
          : "N/A";
    }

    // Update GPU
    const gpuEl = document.getElementById("gpuCurrentValue");
    const gpuStatusEl = document.getElementById("gpuStatus");
    if (gpuEl) {
      const gpuValue = data.gpu_percent;
      if (gpuValue !== null && !isNaN(gpuValue)) {
        gpuEl.textContent = gpuValue.toFixed(1) + "%";
        if (gpuAvailable === null && gpuStatusEl) {
          gpuAvailable = true;
          gpuStatusEl.innerHTML =
            '<i class="fas fa-check-circle" style="color: var(--status-success);"></i> GPU detected';
        }
      } else {
        gpuEl.textContent = "N/A";
        if (gpuAvailable === null && gpuStatusEl) {
          gpuAvailable = false;
          gpuStatusEl.innerHTML =
            '<i class="fas fa-times-circle" style="color: var(--text-muted);"></i> No GPU available';
        }
      }
    }

    // Calculate and update Disk I/O rate
    const diskIoEl = document.getElementById("diskIoCurrentValue");
    if (diskIoEl && lastDiskRead !== null && lastTimestamp !== null) {
      const timeDiff = (timestamp - lastTimestamp) / 1000;
      if (timeDiff > 0) {
        const diskReadRate =
          (data.disk_read_mb_total - lastDiskRead) / timeDiff;
        const diskWriteRate =
          (data.disk_write_mb_total - lastDiskWrite!) / timeDiff;
        const totalIoRate =
          Math.max(0, diskReadRate) + Math.max(0, diskWriteRate);
        diskIoEl.textContent = totalIoRate.toFixed(2) + " MB/s";
      }
    }

    // Calculate and update Network I/O rate
    const netIoEl = document.getElementById("netIoCurrentValue");
    if (netIoEl && lastNetSent !== null && lastTimestamp !== null) {
      const timeDiff = (timestamp - lastTimestamp) / 1000;
      if (timeDiff > 0) {
        const netSentRate = (data.net_sent_mb_total - lastNetSent) / timeDiff;
        const netRecvRate = (data.net_recv_mb_total - lastNetRecv!) / timeDiff;
        const totalNetRate =
          Math.max(0, netSentRate) + Math.max(0, netRecvRate);
        netIoEl.textContent = totalNetRate.toFixed(2) + " MB/s";
      }
    }

    // Update Visitor Pool
    const visitorPoolEl = document.getElementById("visitorPoolCurrentValue");
    if (visitorPoolEl) {
      if (
        data.visitor_pool_allocated !== null &&
        data.visitor_pool_total !== null
      ) {
        visitorPoolEl.textContent = `${data.visitor_pool_allocated}/${data.visitor_pool_total}`;
      } else {
        visitorPoolEl.textContent = "N/A";
      }
    }

    // Update Active Users
    const activeUsersEl = document.getElementById("activeUsersCurrentValue");
    if (activeUsersEl) {
      if (data.active_users_count !== null && data.total_users_count !== null) {
        activeUsersEl.textContent = `${data.active_users_count}/${data.total_users_count}`;
      } else {
        activeUsersEl.textContent = "N/A";
      }
    }

    // Store values for next rate calculation
    lastDiskRead = data.disk_read_mb_total;
    lastDiskWrite = data.disk_write_mb_total;
    lastNetSent = data.net_sent_mb_total;
    lastNetRecv = data.net_recv_mb_total;
    lastTimestamp = timestamp;

    return { success: true };
  } catch (error) {
    console.error("[metrics-updater] Error fetching metrics:", error);
    return { success: false, error: String(error) };
  }
}
