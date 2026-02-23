/**
 * AI Panel Jobs Mode
 * Displays SLURM job list with auto-refresh and cancel support.
 * Calls existing REST API at /console/api/jobs/.
 */

import { getCsrfToken } from "../../utils/csrf";

interface SlurmJob {
  job_id: number | string;
  name?: string;
  state: string;
  time_used?: string;
  partition?: string;
  nodes?: string;
  reason?: string;
}

interface JobsResponse {
  success: boolean;
  jobs: SlurmJob[];
  running: number;
  pending: number;
  total: number;
  slurm_available: boolean;
  message?: string;
}

const POLL_INTERVAL = 5000; // 5s when active jobs exist
const IDLE_INTERVAL = 30000; // 30s when all jobs are done

export class AIPanelJobsMode {
  private listEl: HTMLElement | null = null;
  private summaryEl: HTMLElement | null = null;
  private refreshBtn: HTMLElement | null = null;
  private refreshTimer: ReturnType<typeof setInterval> | null = null;
  private initialized = false;

  init(listEl: HTMLElement, summaryEl: HTMLElement): void {
    this.listEl = listEl;
    this.summaryEl = summaryEl;
    this.refreshBtn = document.getElementById("scitex-ai-jobs-refresh");

    if (this.initialized) return;
    this.initialized = true;

    this.refreshBtn?.addEventListener("click", () => {
      this.refreshBtn?.querySelector("i")?.classList.add("fa-spin");
      void this.refresh().finally(() => {
        setTimeout(() => {
          this.refreshBtn?.querySelector("i")?.classList.remove("fa-spin");
        }, 300);
      });
    });

    void this.refresh();
  }

  async refresh(): Promise<void> {
    if (!this.listEl || !this.summaryEl) return;

    try {
      const resp = await fetch("/console/api/jobs/", {
        headers: { "X-CSRFToken": getCsrfToken() },
      });

      if (!resp.ok) {
        this.summaryEl.textContent = `Error: ${resp.status}`;
        return;
      }

      const data: JobsResponse = await resp.json();

      if (!data.slurm_available) {
        this.summaryEl.textContent = "SLURM not available";
        this.listEl.innerHTML = `
          <div class="scitex-ai-jobs-empty">
            <i class="fas fa-server"></i>
            <span>SLURM scheduler is not available on this system.</span>
          </div>`;
        this.stopPolling();
        return;
      }

      // Update summary
      const parts: string[] = [];
      if (data.running > 0) parts.push(`${data.running} running`);
      if (data.pending > 0) parts.push(`${data.pending} pending`);
      if (data.total === 0) {
        this.summaryEl.textContent = "No jobs";
      } else {
        this.summaryEl.textContent =
          parts.length > 0
            ? parts.join(", ")
            : `${data.total} job${data.total === 1 ? "" : "s"}`;
      }

      // Render job list
      if (data.jobs.length === 0) {
        this.listEl.innerHTML = `
          <div class="scitex-ai-jobs-empty">
            <i class="fas fa-check-circle"></i>
            <span>No active SLURM jobs.</span>
          </div>`;
      } else {
        this.listEl.innerHTML = data.jobs
          .map((j) => this.renderJob(j))
          .join("");

        // Bind cancel buttons
        this.listEl
          .querySelectorAll<HTMLButtonElement>("[data-cancel-job]")
          .forEach((btn) => {
            btn.addEventListener("click", (e) => {
              e.preventDefault();
              const id = btn.dataset.cancelJob!;
              void this.cancelJob(id);
            });
          });
      }

      // Auto-refresh scheduling
      const hasActive = data.running > 0 || data.pending > 0;
      this.startPolling(hasActive ? POLL_INTERVAL : IDLE_INTERVAL);
    } catch (err) {
      this.summaryEl.textContent = "Network error";
      this.stopPolling();
    }
  }

  private renderJob(job: SlurmJob): string {
    const stateClass = this.stateClass(job.state);
    const canCancel = job.state === "RUNNING" || job.state === "PENDING";
    const timeStr = job.time_used || job.reason || "";

    return `
      <div class="scitex-ai-job-card ${stateClass}">
        <div class="scitex-ai-job-row">
          <span class="scitex-ai-job-state ${stateClass}">${job.state}</span>
          <span class="scitex-ai-job-name" title="${job.name || ""}">${job.name || `Job ${job.job_id}`}</span>
        </div>
        <div class="scitex-ai-job-row scitex-ai-job-meta">
          <span>ID: ${job.job_id}</span>
          ${job.partition ? `<span>${job.partition}</span>` : ""}
          ${timeStr ? `<span>${timeStr}</span>` : ""}
          ${
            canCancel
              ? `<button class="scitex-ai-job-cancel" data-cancel-job="${job.job_id}" title="Cancel job">
                   <i class="fas fa-times"></i>
                 </button>`
              : ""
          }
        </div>
      </div>`;
  }

  private stateClass(state: string): string {
    switch (state) {
      case "RUNNING":
        return "running";
      case "PENDING":
        return "pending";
      case "COMPLETED":
        return "completed";
      case "FAILED":
      case "NODE_FAIL":
        return "failed";
      case "CANCELLED":
        return "cancelled";
      case "TIMEOUT":
        return "timeout";
      default:
        return "";
    }
  }

  private async cancelJob(jobId: string): Promise<void> {
    try {
      const resp = await fetch(`/console/api/jobs/${jobId}/cancel/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrfToken(),
        },
      });
      if (resp.ok) {
        void this.refresh();
      }
    } catch {
      // refresh will show updated state
      void this.refresh();
    }
  }

  private startPolling(interval: number): void {
    this.stopPolling();
    this.refreshTimer = setInterval(() => void this.refresh(), interval);
  }

  private stopPolling(): void {
    if (this.refreshTimer) {
      clearInterval(this.refreshTimer);
      this.refreshTimer = null;
    }
  }

  destroy(): void {
    this.stopPolling();
    this.initialized = false;
  }
}
