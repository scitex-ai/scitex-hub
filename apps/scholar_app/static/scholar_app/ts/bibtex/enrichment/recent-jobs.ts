/**
 * Recent Jobs Module
 *
 * Handles loading, rendering, and management of recent BibTeX enrichment jobs.
 *
 * @module recent-jobs
 */

import { getCsrfToken, showAlert } from "./ui-utils.js";

/**
 * Recent job interface
 */
export interface RecentJob {
  id: string;
  original_filename: string;
  status: string;
  total_papers: number;
  processed_papers: number;
  failed_papers: number;
  created_at: string | null;
  completed_at: string | null;
  progress_percentage: number;
  project_name: string | null;
}

/**
 * Recent jobs API response
 */
interface RecentJobsResponse {
  success: boolean;
  jobs: RecentJob[];
  total: number;
}

/**
 * Status badge data
 */
interface StatusBadgeData {
  text: string;
  bgColor: string;
  textColor: string;
}

/**
 * Load and display recent jobs
 */
export async function loadRecentJobs(): Promise<void> {
  try {
    const response = await fetch("/scholar/api/bibtex/recent-jobs/");
    if (!response.ok) {
      console.warn("[BibTeX] Failed to load recent jobs:", response.status);
      return;
    }

    const data: RecentJobsResponse = await response.json();

    if (!data.success || !data.jobs || data.jobs.length === 0) {
      showNoJobsMessage();
      return;
    }

    // Hide "no jobs" message and show container
    const noJobsMsg = document.getElementById("noRecentJobsMessage");
    const jobsContainer = document.getElementById("recentJobsContainer");

    if (noJobsMsg) noJobsMsg.style.display = "none";
    if (jobsContainer) {
      jobsContainer.style.display = "flex";
      renderRecentJobs(data.jobs, jobsContainer);
    }
  } catch (error) {
    console.error("[BibTeX] Error loading recent jobs:", error);
  }
}

/**
 * Show "no jobs" message
 */
function showNoJobsMessage(): void {
  const noJobsMsg = document.getElementById("noRecentJobsMessage");
  const jobsContainer = document.getElementById("recentJobsContainer");
  if (noJobsMsg) noJobsMsg.style.display = "block";
  if (jobsContainer) jobsContainer.style.display = "none";
}

/**
 * Deduplicate jobs by filename, keeping the most recent one
 */
function deduplicateJobs(jobs: RecentJob[]): RecentJob[] {
  const jobsByFilename = new Map<string, RecentJob>();

  for (const job of jobs) {
    const filename = job.original_filename;
    const existing = jobsByFilename.get(filename);

    if (!existing) {
      jobsByFilename.set(filename, job);
    } else {
      // Keep the most recent job (compare by created_at or id)
      const existingDate = existing.created_at ? new Date(existing.created_at).getTime() : 0;
      const currentDate = job.created_at ? new Date(job.created_at).getTime() : 0;

      if (currentDate > existingDate) {
        jobsByFilename.set(filename, job);
      }
    }
  }

  return Array.from(jobsByFilename.values());
}

/**
 * Render recent jobs as compact cards
 */
function renderRecentJobs(jobs: RecentJob[], container: HTMLElement): void {
  // Deduplicate jobs by filename, keeping only the most recent
  const uniqueJobs = deduplicateJobs(jobs);

  container.innerHTML = uniqueJobs
    .map((job) => buildJobCard(job))
    .join("");
}

/**
 * Build HTML for a single job card
 */
function buildJobCard(job: RecentJob): string {
  const jobUrl = `/scholar/bibtex/job/${job.id}/`;
  const downloadUrl = `/scholar/api/bibtex/job/${job.id}/download/`;

  return `
    <div class="recent-job-card" style="position: relative; min-width: 180px; max-width: 200px; padding: 0.75rem; border: 1px solid var(--color-border-default); border-radius: 6px; background: var(--color-canvas-subtle); transition: all 0.2s ease; box-shadow: 0 1px 3px rgba(0,0,0,0.12); display: flex; flex-direction: column; gap: 0.6rem;">

      ${buildCloseButton(job.id)}
      ${buildFilenameSection(job, jobUrl)}
      ${buildPaperCount(job, jobUrl)}
      ${buildProgressBar(job)}
      ${buildActionButtons(job, downloadUrl)}

    </div>
  `;
}

/**
 * Build close button
 */
function buildCloseButton(jobId: string): string {
  return `
    <button onclick="event.stopPropagation(); deleteJob('${jobId}')"
            style="position: absolute; top: 0.4rem; right: 0.4rem; background: none; border: none; color: var(--color-fg-muted); cursor: pointer; padding: 3px; border-radius: 3px; font-size: 0.75rem; line-height: 1; transition: all 0.2s; z-index: 10;"
            onmouseover="this.style.background='var(--color-danger-subtle)'; this.style.color='var(--color-danger-fg)';"
            onmouseout="this.style.background='none'; this.style.color='var(--color-fg-muted)';"
            title="Delete job">
      <i class="fas fa-times"></i>
    </button>
  `;
}

/**
 * Build filename section
 */
function buildFilenameSection(job: RecentJob, jobUrl: string): string {
  return `
    <div style="display: flex; align-items: center; gap: 0.4rem; padding-right: 1.2rem; cursor: pointer;" onclick="window.location.href='${jobUrl}'">
      <i class="fas fa-check-circle" style="color: var(--scitex-color-03); font-size: 0.85rem;"></i>
      <div style="font-weight: 500; color: var(--color-fg-default); font-size: 0.8rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1;" title="${job.original_filename}">
        ${job.original_filename}
      </div>
    </div>
  `;
}

/**
 * Build paper count section
 */
function buildPaperCount(job: RecentJob, jobUrl: string): string {
  return `
    <div style="font-size: 0.7rem; color: var(--color-fg-muted); cursor: pointer;" onclick="window.location.href='${jobUrl}'">
      ${job.total_papers || 0} papers
    </div>
  `;
}

/**
 * Build progress bar (if processing)
 */
function buildProgressBar(job: RecentJob): string {
  if (job.status === "processing" && job.progress_percentage !== undefined) {
    return `
      <div style="background: var(--color-border-default); height: 3px; border-radius: 2px; overflow: hidden;">
        <div style="height: 100%; background: var(--scitex-color-03); width: ${job.progress_percentage}%; transition: width 0.3s ease;"></div>
      </div>
    `;
  }
  return "";
}

/**
 * Build action buttons
 */
function buildActionButtons(job: RecentJob, downloadUrl: string): string {
  if (job.status === "completed") {
    return buildCompletedButtons(job, downloadUrl);
  } else {
    return buildDisabledButtons();
  }
}

/**
 * Build buttons for completed jobs
 */
function buildCompletedButtons(job: RecentJob, downloadUrl: string): string {
  return `
    <div style="display: flex; gap: 0.4rem; margin-top: auto;">
      <button onclick="event.stopPropagation(); saveJobToProject('${job.id}')"
              class="btn btn-warning"
              style="flex: 1; padding: 0.4rem; font-size: 0.7rem; display: flex; align-items: center; justify-content: center; gap: 0.3rem; border: none;"
              title="Save to project">
        <i class="fas fa-save" style="font-size: 0.7rem;"></i>
      </button>

      <button onclick="event.stopPropagation(); window.location.href='${downloadUrl}'"
              class="btn btn-success"
              style="flex: 1; padding: 0.4rem; font-size: 0.7rem; display: flex; align-items: center; justify-content: center; gap: 0.3rem; border: none;"
              title="Download enriched BibTeX">
        <i class="fas fa-download" style="font-size: 0.7rem;"></i>
      </button>

      <button onclick="event.stopPropagation(); window.currentBibtexJobId='${job.id}'; showBibtexDiff();"
              class="btn btn-secondary"
              style="flex: 1; padding: 0.4rem; font-size: 0.7rem; display: flex; align-items: center; justify-content: center; gap: 0.3rem; border: none;"
              title="Show what was enhanced">
        <i class="fas fa-code-branch" style="font-size: 0.7rem;"></i>
      </button>

      <button onclick="event.stopPropagation(); window.currentBibtexJobId='${job.id}'; openAllPaperUrls();"
              class="btn btn-info"
              style="flex: 1; padding: 0.4rem; font-size: 0.7rem; display: flex; align-items: center; justify-content: center; gap: 0.3rem; border: none;"
              title="Open all URLs">
        <i class="fas fa-external-link-alt" style="font-size: 0.7rem;"></i>
      </button>
    </div>
  `;
}

/**
 * Build disabled buttons for non-completed jobs
 */
function buildDisabledButtons(): string {
  return `
    <div style="display: flex; gap: 0.4rem; margin-top: auto;">
      <button disabled
              style="flex: 1; padding: 0.4rem; background: var(--color-neutral-muted); border: none; border-radius: 4px; color: var(--color-fg-muted); font-size: 0.7rem; cursor: not-allowed; display: flex; align-items: center; justify-content: center; gap: 0.3rem; opacity: 0.5;">
        <i class="fas fa-save" style="font-size: 0.7rem;"></i>
      </button>
      <button disabled
              style="flex: 1; padding: 0.4rem; background: var(--color-neutral-muted); border: none; border-radius: 4px; color: var(--color-fg-muted); font-size: 0.7rem; cursor: not-allowed; display: flex; align-items: center; justify-content: center; gap: 0.3rem; opacity: 0.5;">
        <i class="fas fa-download" style="font-size: 0.7rem;"></i>
      </button>
      <button disabled
              style="flex: 1; padding: 0.4rem; background: var(--color-neutral-muted); border: none; border-radius: 4px; color: var(--color-fg-muted); font-size: 0.7rem; cursor: not-allowed; display: flex; align-items: center; justify-content: center; gap: 0.3rem; opacity: 0.5;">
        <i class="fas fa-external-link-alt" style="font-size: 0.7rem;"></i>
      </button>
    </div>
  `;
}

/**
 * Get status badge styling data
 */
export function getStatusBadgeData(status: string): StatusBadgeData {
  const badges: Record<string, StatusBadgeData> = {
    completed: {
      text: "Completed",
      bgColor: "var(--scitex-color-03)",
      textColor: "white",
    },
    processing: {
      text: "Processing",
      bgColor: "var(--scitex-color-04)",
      textColor: "var(--color-fg-default)",
    },
    failed: {
      text: "Failed",
      bgColor: "var(--color-danger-emphasis)",
      textColor: "white",
    },
    pending: {
      text: "Pending",
      bgColor: "var(--color-neutral-muted)",
      textColor: "var(--color-fg-default)",
    },
    cancelled: {
      text: "Cancelled",
      bgColor: "var(--color-danger-subtle)",
      textColor: "var(--color-danger-fg)",
    },
  };

  return badges[status] || badges["pending"];
}

/**
 * Delete a job
 */
export async function deleteJob(jobId: string): Promise<void> {
  try {
    const csrfToken = getCsrfToken();
    if (!csrfToken) {
      showAlert("CSRF token not found. Please refresh the page.", "error");
      return;
    }

    const response = await fetch(`/scholar/api/bibtex/job/${jobId}/delete/`, {
      method: "DELETE",
      headers: {
        "X-CSRFToken": csrfToken,
        "Content-Type": "application/json",
      },
    });

    if (response.ok) {
      // Show success alert
      showAlert("Job deleted successfully", "success");
      // Reload recent jobs
      await loadRecentJobs();
    } else {
      const data = await response.json().catch(() => ({}));
      const errorMsg = data.error || "Failed to delete job";
      showAlert(errorMsg, "error");
    }
  } catch (error) {
    console.error("Error deleting job:", error);
    showAlert("Failed to delete job", "error");
  }
}
