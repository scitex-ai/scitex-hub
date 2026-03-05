/**
 * Jobs Panel Manager
 * Manages the SLURM jobs panel in the code workspace
 */

interface SlurmJob {
  job_id: number;
  name: string;
  user: string;
  state: string;
  time_used: string;
  time_limit: string;
  cpus: string;
  memory: string;
  partition: string;
  node: string | null;
  reason: string | null;
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

export class JobsPanelManager {
  private refreshInterval: number | null = null;
  private isJobsViewActive = false;
  private lastJobCount = 0;

  constructor() {
    console.log("[JobsPanelManager] Constructor called");
    this.initializePanelTabs();
    this.initializeJobsToolbar();
    this.startBackgroundRefresh();
  }

  /**
   * Initialize panel tab switching (Terminal / Jobs)
   */
  private initializePanelTabs(): void {
    console.log("[JobsPanelManager] initializePanelTabs called");
    const jobsTab = document.getElementById("panel-tab-jobs");
    const terminalView = document.getElementById("terminal-view");
    const jobsView = document.getElementById("jobs-view");

    console.log("[JobsPanelManager] Elements found:", {
      jobsTab: !!jobsTab,
      terminalView: !!terminalView,
      jobsView: !!jobsView,
    });

    if (!jobsTab || !terminalView || !jobsView) {
      console.warn(
        "[JobsPanelManager] Panel elements not found - will retry on DOMContentLoaded",
      );
      if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", () =>
          this.initializePanelTabs(),
        );
      }
      return;
    }

    // Jobs tab toggles between jobs view and terminal view
    jobsTab.addEventListener("click", () => {
      console.log("[JobsPanelManager] Jobs tab clicked");
      if (this.isJobsViewActive) {
        this.switchToPanel("terminal");
      } else {
        this.switchToPanel("jobs");
      }
    });

    // When any terminal tab is clicked, switch back to terminal view
    const terminalTabs = document.getElementById("terminal-tabs");
    if (terminalTabs) {
      terminalTabs.addEventListener("click", (e) => {
        const tab = (e.target as HTMLElement).closest(".terminal-tab");
        if (tab && this.isJobsViewActive) {
          this.switchToPanel("terminal");
        }
      });
    }

    console.log("[JobsPanelManager] Panel tabs initialized successfully");
  }

  /**
   * Switch between terminal and jobs panels
   */
  private switchToPanel(panel: "terminal" | "jobs"): void {
    const jobsTab = document.getElementById("panel-tab-jobs");
    const terminalView = document.getElementById("terminal-view");
    const jobsView = document.getElementById("jobs-view");

    if (!jobsTab || !terminalView || !jobsView) return;

    if (panel === "terminal") {
      jobsTab.classList.remove("active");
      terminalView.classList.add("active");
      jobsView.classList.remove("active");
      this.isJobsViewActive = false;
    } else {
      jobsTab.classList.add("active");
      terminalView.classList.remove("active");
      jobsView.classList.add("active");
      this.isJobsViewActive = true;
      this.refreshJobs();
    }
  }

  /**
   * Initialize jobs toolbar buttons
   */
  private initializeJobsToolbar(): void {
    const refreshBtn = document.getElementById("jobs-refresh");
    const cancelPendingBtn = document.getElementById("jobs-cancel-pending");

    refreshBtn?.addEventListener("click", () => {
      this.refreshJobs(true);
    });

    cancelPendingBtn?.addEventListener("click", () => {
      this.cancelAllPending();
    });
  }

  /**
   * Start background refresh for job badge updates
   */
  private startBackgroundRefresh(): void {
    // Initial load
    this.updateJobBadge();

    // Background refresh every 10 seconds for badge
    this.refreshInterval = window.setInterval(() => {
      if (this.isJobsViewActive) {
        this.refreshJobs();
      } else {
        this.updateJobBadge();
      }
    }, 10000);
  }

  /**
   * Update just the job count badge (lightweight)
   */
  private async updateJobBadge(): Promise<void> {
    try {
      const response = await fetch("/console/api/jobs/");
      const data: JobsResponse = await response.json();

      const activeJobs = data.running + data.pending;
      for (const id of ["jobs-badge"]) {
        const el = document.getElementById(id);
        if (!el) continue;
        el.textContent = String(activeJobs);
        el.style.display = "inline-flex";
      }
      this.lastJobCount = activeJobs;
    } catch (error) {
      console.warn("[JobsPanelManager] Failed to update badge:", error);
    }
  }

  /**
   * Refresh the full jobs list
   */
  public async refreshJobs(showSpinner = false): Promise<void> {
    const jobsList = document.getElementById("jobs-list");
    const refreshBtn = document.getElementById("jobs-refresh");
    const statusText = document.getElementById("jobs-status-text");
    const statusDot = document.querySelector(".jobs-status-dot");
    if (!jobsList) return;
    // Show spinner on refresh button
    if (showSpinner && refreshBtn) {
      const icon = refreshBtn.querySelector("i");
      icon?.classList.add("spinning");
    }

    try {
      const response = await fetch("/console/api/jobs/");
      const data: JobsResponse = await response.json();

      // Update status indicator
      if (statusDot) {
        statusDot.classList.remove("error");
        statusDot.classList.add("connected");
      }

      // Check if SLURM is available
      if (!data.slurm_available) {
        jobsList.innerHTML = `
          <div class="jobs-unavailable">
            <i class="fas fa-exclamation-triangle"></i>
            <span>SLURM is not available on this system</span>
          </div>
        `;
        if (statusText) statusText.textContent = "SLURM unavailable";
        return;
      }

      // Update status text
      if (statusText) {
        statusText.textContent = `${data.running} running, ${data.pending} pending`;
      }

      // Update badge
      this.updateJobBadge();

      // Render jobs
      if (data.jobs.length === 0) {
        jobsList.innerHTML = `
          <div class="jobs-empty">
            <i class="fas fa-check-circle"></i>
            <span class="jobs-empty-text">No active jobs</span>
          </div>
        `;
        return;
      }

      // Group jobs by state
      const runningJobs = data.jobs.filter((j) => j.state === "RUNNING");
      const pendingJobs = data.jobs.filter((j) => j.state === "PENDING");
      const otherJobs = data.jobs.filter(
        (j) => !["RUNNING", "PENDING"].includes(j.state),
      );

      let html = "";

      if (runningJobs.length > 0) {
        html += this.renderJobSection("running", "Running", runningJobs);
      }

      if (pendingJobs.length > 0) {
        html += this.renderJobSection("pending", "Pending", pendingJobs);
      }

      if (otherJobs.length > 0) {
        html += this.renderJobSection("other", "Other", otherJobs, true);
      }

      jobsList.innerHTML = html;

      // Attach event listeners for job cards
      this.attachJobCardListeners();
    } catch (error) {
      console.error("[JobsPanelManager] Failed to refresh jobs:", error);

      if (statusDot) {
        statusDot.classList.remove("connected");
        statusDot.classList.add("error");
      }
      if (statusText) {
        statusText.textContent = "Connection error";
      }

      jobsList.innerHTML = `
        <div class="jobs-unavailable">
          <i class="fas fa-exclamation-circle"></i>
          <span>Failed to load jobs</span>
        </div>
      `;
    } finally {
      // Remove spinner
      if (refreshBtn) {
        const icon = refreshBtn.querySelector("i");
        icon?.classList.remove("spinning");
      }
    }
  }

  /**
   * Render a section of jobs (Running, Pending, etc.)
   */
  private renderJobSection(
    type: string,
    title: string,
    jobs: SlurmJob[],
    collapsed = false,
  ): string {
    const iconClass =
      type === "running"
        ? "running"
        : type === "pending"
          ? "pending"
          : "completed";

    return `
      <div class="jobs-section ${collapsed ? "collapsed" : ""}" data-section="${type}">
        <div class="jobs-section-header">
          <span class="jobs-section-icon ${iconClass}"></span>
          <span class="jobs-section-title">${title}</span>
          <span class="jobs-section-count">(${jobs.length})</span>
          <i class="fas fa-chevron-down jobs-section-chevron"></i>
        </div>
        <div class="jobs-section-items">
          ${jobs.map((job) => this.renderJobCard(job)).join("")}
        </div>
      </div>
    `;
  }

  /**
   * Render a single job card
   */
  private renderJobCard(job: SlurmJob): string {
    const statusClass =
      job.state === "RUNNING"
        ? "running"
        : job.state === "PENDING"
          ? "pending"
          : job.state === "COMPLETED"
            ? "completed"
            : "failed";
    const showReason = job.state === "PENDING" && job.reason;
    return `
      <div class="job-card" data-job-id="${job.job_id}">
        <div class="job-card-header">
          <span class="job-card-status ${statusClass}"></span>
          <span class="job-card-id">#${job.job_id}</span>
          <span class="job-card-name" title="${job.name}">${job.name}</span>
          <span class="job-card-time">${job.time_used}</span>
        </div>
        <div class="job-card-details">
          <span class="job-card-detail">
            <i class="fas fa-layer-group"></i>
            ${job.partition}
          </span>
          <span class="job-card-detail">
            <i class="fas fa-microchip"></i>
            ${job.cpus} CPU
          </span>
          <span class="job-card-detail">
            <i class="fas fa-memory"></i>
            ${job.memory}
          </span>
          ${
            job.node
              ? `
            <span class="job-card-detail">
              <i class="fas fa-server"></i>
              ${job.node}
            </span>
          `
              : ""
          }
        </div>
        ${
          showReason
            ? `
          <div class="job-card-reason">
            <i class="fas fa-info-circle"></i> ${job.reason}
          </div>
        `
            : ""
        }
        <div class="job-card-actions">
          ${
            job.state !== "COMPLETED"
              ? `
            <button class="job-card-btn cancel" data-action="cancel" data-job-id="${job.job_id}">
              <i class="fas fa-times"></i> Cancel
            </button>
          `
              : ""
          }
        </div>
      </div>
    `;
  }

  /**
   * Attach event listeners to job cards
   */
  private attachJobCardListeners(): void {
    // Section collapse/expand
    document.querySelectorAll(".jobs-section-header").forEach((header) => {
      header.addEventListener("click", () => {
        const section = header.closest(".jobs-section");
        section?.classList.toggle("collapsed");
      });
    });

    // Cancel buttons
    document
      .querySelectorAll('.job-card-btn[data-action="cancel"]')
      .forEach((btn) => {
        btn.addEventListener("click", (e) => {
          e.stopPropagation();
          const jobId = (btn as HTMLElement).dataset.jobId;
          if (jobId) {
            this.cancelJob(parseInt(jobId));
          }
        });
      });
  }

  /**
   * Cancel a single job
   */
  public async cancelJob(jobId: number): Promise<void> {
    try {
      const csrfToken = (
        document.querySelector(
          'input[name="csrfmiddlewaretoken"]',
        ) as HTMLInputElement
      )?.value;

      const response = await fetch(`/code/api/jobs/${jobId}/cancel/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken || "",
        },
      });

      const data = await response.json();

      if (data.success) {
        console.log(`[JobsPanelManager] Job ${jobId} cancelled`);
        this.refreshJobs();
      } else {
        alert(`Failed to cancel job: ${data.message}`);
      }
    } catch (error) {
      console.error("[JobsPanelManager] Cancel failed:", error);
      alert("Failed to cancel job");
    }
  }

  /**
   * Cancel all pending jobs
   */
  public async cancelAllPending(): Promise<void> {
    const pendingJobs = document.querySelectorAll(
      '.jobs-section[data-section="pending"] .job-card',
    );

    if (pendingJobs.length === 0) {
      alert("No pending jobs to cancel");
      return;
    }

    const csrfToken = (
      document.querySelector(
        'input[name="csrfmiddlewaretoken"]',
      ) as HTMLInputElement
    )?.value;

    let cancelled = 0;
    let failed = 0;

    for (const card of Array.from(pendingJobs)) {
      const jobId = (card as HTMLElement).dataset.jobId;
      if (!jobId) continue;

      try {
        const response = await fetch(`/code/api/jobs/${jobId}/cancel/`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken || "",
          },
        });

        const data = await response.json();
        if (data.success) {
          cancelled++;
        } else {
          failed++;
        }
      } catch {
        failed++;
      }
    }

    console.log(
      `[JobsPanelManager] Cancelled ${cancelled} jobs, ${failed} failed`,
    );
    this.refreshJobs();

    if (failed > 0) {
      alert(`Cancelled ${cancelled} jobs, ${failed} failed`);
    }
  }

  /**
   * Cleanup on destroy
   */
  public destroy(): void {
    if (this.refreshInterval) {
      window.clearInterval(this.refreshInterval);
      this.refreshInterval = null;
    }
  }
}
