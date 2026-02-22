/**

 * BibTeX Enrichment Queue Management System
 *
 * Handles:
 * - Resource monitoring and display
 * - Queue position visualization
 * - Job cancellation
 * - Privacy/security (only show user's own jobs)
 *
 * @requires Django CSRF token in page
 * @requires URL endpoints configured
 *
 * @version 1.0.0
 */

/**
 * Job data interface
 */

console.log(
  "[DEBUG] apps/scholar_app/static/scholar_app/ts/bibtex/queue-management.ts loaded",
);
interface JobData {
  id: string;
  filename: string;
  progress: number;
  processed: number;
  total: number;
  can_cancel: boolean;
  position?: number;
}

/**
 * Jobs response interface
 */
interface JobsData {
  active: JobData[];
  queued: JobData[];
  active_count: number;
  queued_count: number;
}

/**
 * System stats interface
 */
interface SystemStats {
  cpu_percent: string;
  memory_percent: string;
}

/**
 * Resource status response interface
 */
interface ResourceStatusResponse {
  system: SystemStats;
  jobs: JobsData;
  timestamp: string;
}

/**
 * Queue management configuration
 */
interface QueueConfig {
  resourceStatusUrl?: string;
  pollInterval?: number;
}

// Global state
let resourceMonitorInterval: number | null = null;

/**
 * Initialize queue management system
 */
function initQueueManagement(config: QueueConfig = {}): void {
  console.log("[Queue Management] initQueueManagement() called");
  const {
    resourceStatusUrl = "/scholar/api/bibtex/resource-status/",
    pollInterval = 2000,
  } = config;

  // Start monitoring when page loads
  updateResourceMonitor(resourceStatusUrl);

  // Poll every 2 seconds
  if (resourceMonitorInterval) {
    console.log("[Queue Management] Clearing existing interval");
    clearInterval(resourceMonitorInterval);
  }
  console.log(
    "[Queue Management] Starting new interval with",
    pollInterval,
    "ms interval",
  );
  resourceMonitorInterval = window.setInterval(() => {
    updateResourceMonitor(resourceStatusUrl);
  }, pollInterval);
}

/**
 * Stop queue management monitoring
 */
function stopQueueManagement(): void {
  console.log(
    "[Queue Management] stopQueueManagement() called, interval exists:",
    !!resourceMonitorInterval,
  );
  if (resourceMonitorInterval) {
    clearInterval(resourceMonitorInterval);
    resourceMonitorInterval = null;
    console.log("[Queue Management] Interval cleared and set to null");
  }
}

/**
 * Update resource monitor display
 */
function updateResourceMonitor(resourceStatusUrl: string): void {
  fetch(resourceStatusUrl)
    .then((response) => response.json())
    .then((data: ResourceStatusResponse) => {
      updateSystemStats(data.system);
      updateActiveJobs(data.jobs);
      updateQueuedJobs(data.jobs);
      updateRefreshTime(data.timestamp);
    })
    .catch((error: Error) => {
      console.error("Failed to fetch resource status:", error);
      const refreshTimeEl = document.getElementById(
        "resourceRefreshTime",
      ) as HTMLElement | null;
      if (refreshTimeEl) {
        refreshTimeEl.textContent = "Error fetching data";
      }
    });
}

/**
 * Update system statistics display
 */
function updateSystemStats(system: SystemStats): void {
  const cpuElement = document.getElementById(
    "cpuPercent",
  ) as HTMLElement | null;
  const memoryElement = document.getElementById(
    "memoryPercent",
  ) as HTMLElement | null;

  if (cpuElement) cpuElement.textContent = system.cpu_percent;
  if (memoryElement) memoryElement.textContent = system.memory_percent;
}

/**
 * Update active jobs display
 */
function updateActiveJobs(jobs: JobsData): void {
  const activeJobsCount = document.getElementById(
    "activeJobsCount",
  ) as HTMLElement | null;
  const activeJobsList = document.getElementById(
    "activeJobsList",
  ) as HTMLElement | null;
  const activeJobsContent = document.getElementById(
    "activeJobsContent",
  ) as HTMLElement | null;

  if (!activeJobsList || !activeJobsContent) return;

  // Update count
  if (activeJobsCount)
    activeJobsCount.textContent = jobs.active_count.toString();

  // Show active list if user has active jobs OR if there are system active jobs
  if (jobs.active.length > 0) {
    activeJobsList.style.display = "block";
    activeJobsContent.innerHTML = jobs.active
      .map((job) => renderActiveJob(job))
      .join("");
  } else if (jobs.active_count > 0) {
    // System has active jobs, but none belong to this user
    activeJobsList.style.display = "block";
    activeJobsContent.innerHTML = renderPrivacyMessage(
      jobs.active_count,
      "currently processing",
    );
  } else {
    activeJobsList.style.display = "none";
  }
}

/**
 * Render a single active job card
 */
function renderActiveJob(job: JobData): string {
  return `
        <div style="background: var(--color-canvas-default); padding: 0.75rem; border-radius: 6px; margin-bottom: 0.5rem; border-left: 3px solid var(--scitex-color-03); animation: pulse 2s infinite;">
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.25rem;">
                <div style="color: var(--color-fg-default); font-weight: 600; font-size: 0.9rem;">
                    <i class="fas fa-cog fa-spin"></i> ${escapeHtml(job.filename)}
                </div>
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    ${
                      job.can_cancel
                        ? `
                        <button onclick="cancelJob('${job.id}')" style="background: var(--error-color); color: var(--white); border: none; border-radius: 4px; padding: 0.25rem 0.5rem; cursor: pointer; font-size: 0.75rem;" title="Cancel job">
                            <i class="fas fa-times"></i>
                        </button>
                    `
                        : ""
                    }
                </div>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div style="flex: 1; margin-right: 1rem;">
                    <div style="background: var(--color-border-default); border-radius: 4px; height: 6px; overflow: hidden;">
                        <div style="background: var(--scitex-color-03); height: 100%; width: ${job.progress}%; transition: width 0.3s;"></div>
                    </div>
                </div>
                <div style="color: var(--color-fg-muted); font-size: 0.85rem; white-space: nowrap;">
                    ${job.progress}% (${job.processed}/${job.total})
                </div>
            </div>
        </div>
    `;
}

/**
 * Update queued jobs display
 */
function updateQueuedJobs(jobs: JobsData): void {
  const queuedJobsCount = document.getElementById(
    "queuedJobsCount",
  ) as HTMLElement | null;
  const queuedJobsList = document.getElementById(
    "queuedJobsList",
  ) as HTMLElement | null;
  const queuedJobsContent = document.getElementById(
    "queuedJobsContent",
  ) as HTMLElement | null;

  if (!queuedJobsList || !queuedJobsContent) return;

  // Update count
  if (queuedJobsCount)
    queuedJobsCount.textContent = jobs.queued_count.toString();

  // Show queued list if user has queued jobs OR if there are system queues
  if (jobs.queued.length > 0) {
    queuedJobsList.style.display = "block";
    queuedJobsContent.innerHTML = jobs.queued
      .map((job) => renderQueuedJob(job))
      .join("");
  } else if (jobs.queued_count > 0) {
    // System has queued jobs, but none belong to this user
    queuedJobsList.style.display = "block";
    queuedJobsContent.innerHTML = renderPrivacyMessage(
      jobs.queued_count,
      "in system queue",
    );
  } else {
    queuedJobsList.style.display = "none";
  }
}

/**
 * Render a single queued job card with position indicator
 */
function renderQueuedJob(job: JobData): string {
  // Visual indicator based on queue position
  const position = job.position || 0;
  const positionColor =
    position === 1
      ? "var(--success-color)"
      : position === 2
        ? "var(--scitex-color-03)"
        : "var(--warning-color)";
  const positionBadge =
    position === 1
      ? '<i class="fas fa-star"></i> Next up'
      : position === 2
        ? '<i class="fas fa-arrow-up"></i> 2nd in line'
        : `<i class="fas fa-hourglass-half"></i> Position #${position}`;

  return `
        <div style="background: var(--color-canvas-default); padding: 0.75rem; border-radius: 6px; margin-bottom: 0.5rem; border-left: 3px solid ${positionColor};">
            <div style="display: flex; justify-content: space-between; align-items: start;">
                <div style="flex: 1;">
                    <div style="color: var(--color-fg-default); font-weight: 600; font-size: 0.9rem; margin-bottom: 0.25rem;">
                        <i class="fas fa-file-code"></i> ${escapeHtml(job.filename)}
                    </div>
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <span style="color: ${positionColor}; font-size: 0.85rem; font-weight: 600;">
                            ${positionBadge}
                        </span>
                        ${
                          position > 3
                            ? `
                            <span style="color: var(--color-fg-muted); font-size: 0.75rem;">
                                (${position - 1} jobs ahead)
                            </span>
                        `
                            : ""
                        }
                    </div>
                </div>
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    ${
                      job.can_cancel
                        ? `
                        <button onclick="cancelJob('${job.id}')" style="background: var(--error-color); color: var(--white); border: none; border-radius: 4px; padding: 0.25rem 0.5rem; cursor: pointer; font-size: 0.75rem;" title="Cancel job">
                            <i class="fas fa-times"></i>
                        </button>
                    `
                        : ""
                    }
                </div>
            </div>
        </div>
    `;
}

/**
 * Render privacy message when other users have jobs
 */
function renderPrivacyMessage(count: number, status: string): string {
  return `
        <div style="background: var(--color-canvas-subtle); padding: 1rem; border-radius: 6px; text-align: center; color: var(--color-fg-muted);">
            <i class="fas fa-info-circle"></i> ${count} job(s) ${status}
            <div style="font-size: 0.85rem; margin-top: 0.25rem;">
                (Other users' jobs - hidden for privacy)
            </div>
        </div>
    `;
}

/**
 * Update refresh time display
 */
function updateRefreshTime(timestamp: string): void {
  const refreshTimeElement = document.getElementById(
    "resourceRefreshTime",
  ) as HTMLElement | null;
  if (refreshTimeElement) {
    const updateTime = new Date(timestamp);
    refreshTimeElement.textContent = `Updated ${updateTime.toLocaleTimeString()}`;
  }
}

/**
 * Cancel a job (called from inline onclick)
 */
(window as any).cancelJob = function (jobId: string): void {
  // Get CSRF token
  const csrfToken = (
    document.querySelector("[name=csrfmiddlewaretoken]") as HTMLInputElement
  )?.value;
  if (!csrfToken) {
    alert("Security token not found. Please refresh the page.");
    return;
  }

  fetch(`/scholar/api/bibtex/job/${jobId}/cancel/`, {
    method: "POST",
    headers: {
      "X-Requested-With": "XMLHttpRequest",
      "X-CSRFToken": csrfToken,
      "Content-Type": "application/json",
    },
  })
    .then((response) => response.json())
    .then((data: any) => {
      if (data.success) {
        alert("Job cancelled successfully");
        // Refresh status immediately
        updateResourceMonitor("/scholar/api/bibtex/resource-status/");
      } else {
        alert(`Failed to cancel job: ${data.error}`);
      }
    })
    .catch((error: Error) => {
      console.error("Error cancelling job:", error);
      alert("Failed to cancel job. Please try again.");
    });
};

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text: string): string {
  const map: { [key: string]: string } = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  };
  return text.replace(/[&<>"']/g, (m) => map[m]);
}

/**
 * Check if queue management should be active
 */
function shouldRunQueueManagement(): boolean {
  const pathname = window.location.pathname;
  const hash = window.location.hash;
  // Check if we're on the bibtex page (/scholar/bibtex/) or if #bibtex is in hash (legacy)
  const shouldRun = pathname.includes("/bibtex/") || hash.includes("#bibtex");
  console.log(
    "[Queue Management] Checking if should run. Pathname:",
    pathname,
    "Hash:",
    hash,
    "Should run:",
    shouldRun,
  );
  return shouldRun;
}

// Auto-initialize when DOM is ready - only if on bibtex tab
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    if (shouldRunQueueManagement()) {
      initQueueManagement();
    }
  });
} else {
  if (shouldRunQueueManagement()) {
    initQueueManagement();
  }
}

// Cleanup on page unload
window.addEventListener("beforeunload", () => {
  stopQueueManagement();
});

// Start/stop queue management based on hash changes
window.addEventListener("hashchange", () => {
  if (shouldRunQueueManagement()) {
    if (!resourceMonitorInterval) {
      initQueueManagement();
    }
  } else {
    stopQueueManagement();
  }
});
