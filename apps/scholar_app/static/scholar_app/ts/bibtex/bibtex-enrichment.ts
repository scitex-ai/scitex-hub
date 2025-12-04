/**
 * BibTeX Enrichment Orchestrator
 *
 * Coordinates the complete BibTeX enrichment workflow by orchestrating
 * specialized modules for file upload, job polling, actions, diff display,
 * and recent jobs management.
 *
 * @version 2.0.0
 */

import { FileUploadManager } from "./enrichment/file-upload.js";
import { JobPollingManager } from "./enrichment/job-polling.js";
import {
  autoDownloadBibtexFile,
  openAllPaperUrls,
  saveJobToProject,
} from "./enrichment/job-actions.js";
import {
  showBibtexDiff,
  closeBibtexDiff,
  toggleProcessingLogVisibility,
} from "./enrichment/diff-display.js";
import { loadRecentJobs, deleteJob } from "./enrichment/recent-jobs.js";
import {
  showAlert,
  resetBibtexForm,
  getCsrfToken,
} from "./enrichment/ui-utils.js";

console.log(
  "[DEBUG] apps/scholar_app/static/scholar_app/ts/bibtex/bibtex-enrichment.ts loaded",
);

// Global state
declare global {
  interface Window {
    currentBibtexJobId: string | null;
    SCHOLAR_CONFIG?: {
      urls?: {
        bibtexUpload?: string;
        resourceStatus?: string;
      };
    };
  }
}

window.currentBibtexJobId = null;

/**
 * BibTeX enrichment configuration
 */
interface BibtexEnrichmentConfig {
  formId?: string;
  fileInputId?: string;
  dropZoneId?: string;
  statusPollInterval?: number;
}

/**
 * BibTeX Enrichment Orchestrator Class
 */
class BibtexEnrichmentOrchestrator {
  private fileUploadManager: FileUploadManager;
  private jobPollingManager: JobPollingManager;
  private config: BibtexEnrichmentConfig;

  constructor(config: BibtexEnrichmentConfig = {}) {
    this.config = {
      formId: config.formId || "bibtexEnrichmentForm",
      fileInputId: config.fileInputId || "bibtexFileInput",
      dropZoneId: config.dropZoneId || "dropZone",
      statusPollInterval: config.statusPollInterval || 2000,
    };

    // Initialize file upload manager
    this.fileUploadManager = new FileUploadManager({
      formId: this.config.formId!,
      fileInputId: this.config.fileInputId!,
      dropZoneId: this.config.dropZoneId!,
      onSubmit: this.handleFormSubmit.bind(this),
    });

    // Initialize job polling manager
    this.jobPollingManager = new JobPollingManager(
      this.config.statusPollInterval,
      this.handleJobCompletion.bind(this),
      this.handleJobFailure.bind(this),
    );

    console.log("[BibTeX Enrichment] Orchestrator initialized");
  }

  /**
   * Handle form submission
   */
  private async handleFormSubmit(formData: FormData): Promise<void> {
    const csrfToken = getCsrfToken();

    if (!csrfToken) {
      alert("CSRF token not found. Please refresh the page.");
      return;
    }

    const uploadUrl =
      window.SCHOLAR_CONFIG?.urls?.bibtexUpload ||
      "/scholar/bibtex/upload/";

    try {
      const response = await fetch(uploadUrl, {
        method: "POST",
        body: formData,
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": csrfToken,
        },
      });

      if (response.status === 409) {
        // Conflict - user already has a job in progress
        await this.handleJobConflict(response, formData, uploadUrl, csrfToken);
        return;
      }

      const data = await response.json();

      if (data.success && data.job_id) {
        window.currentBibtexJobId = data.job_id;

        if (data.cached) {
          // Show cached result notification
          showAlert(data.message || "Using cached enrichment result", "info");
          // Skip polling, job is already completed - enable buttons
          this.handleJobCompletion(data.job_id);
        } else {
          // Start polling for job status
          this.jobPollingManager.pollJobStatus(data.job_id);
        }
      } else {
        alert("Error: " + (data.error || "Failed to start enrichment"));
        resetBibtexForm();
      }
    } catch (error: any) {
      console.error("Error:", error);
      if (!this.isIgnoredError(error.message)) {
        alert("Failed to upload BibTeX file: " + error.message);
        resetBibtexForm();
      }
    }
  }

  /**
   * Handle job conflict (409)
   */
  private async handleJobConflict(
    response: Response,
    formData: FormData,
    uploadUrl: string,
    csrfToken: string,
  ): Promise<void> {
    const data = await response.json();

    if (data.requires_confirmation && data.existing_job) {
      const msg = `You already have a job in progress: "${data.existing_job.filename}" (${data.existing_job.progress}% complete).\n\nCancel it and start a new job?`;

      if (confirm(msg)) {
        // Resubmit with force flag
        formData.append("force", "true");
        const retryResponse = await fetch(uploadUrl, {
          method: "POST",
          body: formData,
          headers: {
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRFToken": csrfToken,
          },
        });
        const retryData = await retryResponse.json();

        if (retryData.success && retryData.job_id) {
          this.jobPollingManager.pollJobStatus(retryData.job_id);
          window.currentBibtexJobId = retryData.job_id;
        }
      } else {
        // User declined, start monitoring existing job
        if (data.existing_job.id) {
          this.jobPollingManager.pollJobStatus(data.existing_job.id);
          window.currentBibtexJobId = data.existing_job.id;
        }
      }
    } else {
      alert(
        data.message ||
          "You already have a job in progress. Please wait for it to complete.",
      );
      resetBibtexForm();
    }
  }

  /**
   * Check if error should be ignored
   */
  private isIgnoredError(message: string): boolean {
    const ignoredErrors = [
      "Job already running",
      "User declined to cancel existing job",
    ];
    return ignoredErrors.includes(message);
  }

  /**
   * Handle job completion
   */
  private handleJobCompletion(jobId: string): void {
    console.log("[Orchestrator] Job completed:", jobId);

    // Enable action buttons for completed job
    this.enableActionButtonsForJob(jobId);
  }

  /**
   * Enable action buttons for a completed job (used for cached results)
   */
  private enableActionButtonsForJob(jobId: string): void {
    // Show that job is ready
    const runningIndicator = document.getElementById("enrichmentRunningIndicator");
    if (runningIndicator) {
      runningIndicator.style.display = "none";
    }

    // Enable buttons
    const buttons = ["downloadBtn", "saveToProjectBtn", "viewChangesBtn", "openUrlsMainBtn"];
    buttons.forEach(id => {
      const btn = document.getElementById(id) as HTMLButtonElement | null;
      if (btn) {
        btn.disabled = false;
        btn.style.opacity = "1";
        btn.style.cursor = "pointer";
      }
    });

    // Update URL count
    this.updateUrlCountForJob(jobId);
  }

  /**
   * Update URL count for job
   */
  private async updateUrlCountForJob(jobId: string): Promise<void> {
    try {
      const response = await fetch(`/scholar/api/bibtex/job/${jobId}/urls/`);
      const urlData = await response.json();
      const count = urlData.total_urls || 0;

      const urlButtonText = document.getElementById("urlButtonText");
      if (urlButtonText && count > 0) {
        urlButtonText.textContent = `Open All ${count} URLs`;
      }
    } catch (error) {
      console.error("[BibTeX] Failed to fetch URL count:", error);
    }
  }

  /**
   * Handle job failure
   */
  private handleJobFailure(jobId: string, error?: string): void {
    console.log("[Orchestrator] Job failed:", jobId, error);
    // Failure handling is already done in JobPollingManager
  }
}

/**
 * Initialize BibTeX enrichment system
 */
function initBibtexEnrichment(config: BibtexEnrichmentConfig = {}): void {
  try {
    new BibtexEnrichmentOrchestrator(config);
  } catch (error) {
    console.warn("[BibTeX Enrichment] Initialization failed:", error);
  }
}

// Global window functions for template access
(window as any).handleDownload = async function (): Promise<void> {
  const downloadBtn = document.getElementById(
    "downloadBtn",
  ) as HTMLButtonElement;
  if (!downloadBtn) return;

  const jobId = window.currentBibtexJobId;
  if (!jobId) {
    showAlert(
      "⚠ No enriched file available yet. Please wait for enrichment to complete.",
      "warning",
    );
    return;
  }

  const downloadUrl = `/scholar/api/bibtex/job/${jobId}/download/`;

  const originalHTML = downloadBtn.innerHTML;
  downloadBtn.disabled = true;
  downloadBtn.innerHTML =
    '<i class="fas fa-spinner fa-spin"></i> Downloading...';
  downloadBtn.style.opacity = "0.7";

  try {
    await autoDownloadBibtexFile(downloadUrl);
  } catch (error) {
    console.error("[Handle Download] Error:", error);
    showAlert(
      "❌ Failed to download enriched BibTeX file. Please try again.",
      "error",
    );
  } finally {
    downloadBtn.disabled = false;
    downloadBtn.innerHTML = originalHTML;
    downloadBtn.style.opacity = "1";
  }
};

(window as any).openAllPaperUrls = function (): void {
  const jobId = window.currentBibtexJobId;
  if (!jobId) {
    alert("No job ID available. Please wait for enrichment to complete.");
    return;
  }
  openAllPaperUrls(jobId);
};

(window as any).showBibtexDiff = function (): void {
  const jobId = window.currentBibtexJobId;
  if (!jobId) {
    alert("No job ID available. Please wait for enrichment to complete.");
    return;
  }
  showBibtexDiff(jobId);
};

(window as any).closeBibtexDiff = closeBibtexDiff;
(window as any).toggleProcessingLogVisibility = toggleProcessingLogVisibility;

(window as any).handleSaveToProject = async function (): Promise<void> {
  const saveBtn = document.getElementById(
    "saveToProjectBtn",
  ) as HTMLButtonElement;
  if (!saveBtn) return;

  const originalHTML = saveBtn.innerHTML;
  saveBtn.disabled = true;
  saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
  saveBtn.style.opacity = "0.7";

  try {
    const jobId = window.currentBibtexJobId;
    if (!jobId) {
      throw new Error("No job ID found");
    }

    await saveJobToProject(jobId);
  } catch (error) {
    console.error("[Handle Save] Error:", error);
    showAlert("Failed to save to project. Please try again.", "error");
  } finally {
    saveBtn.disabled = false;
    saveBtn.innerHTML = originalHTML;
    saveBtn.style.opacity = "1";
  }
};

(window as any).saveJobToProject = saveJobToProject;
(window as any).deleteJob = deleteJob;

// Initialize on DOM ready
document.addEventListener("DOMContentLoaded", function () {
  initBibtexEnrichment();
  loadRecentJobs();
});
