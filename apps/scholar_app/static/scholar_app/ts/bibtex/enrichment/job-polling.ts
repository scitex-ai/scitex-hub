/**
 * Job Polling Module
 *
 * Handles BibTeX job status polling, progress updates, and log management.
 *
 * @module job-polling
 */

import {
  updateElementText,
  setElementVisibility,
  scrollToBottom,
  setButtonState,
} from "./ui-utils.js";

/**
 * Job status response interface
 */
export interface JobStatusResponse {
  status: string;
  progress_percentage?: number;
  processed_papers?: number;
  total_papers?: number;
  failed_papers?: number;
  log?: string;
  error_message?: string;
}

/**
 * Job completion callback
 */
export type JobCompletionCallback = (jobId: string) => void;

/**
 * Job polling manager class
 */
export class JobPollingManager {
  private pollInterval: number;
  private maxAttempts: number = 180;
  private onComplete?: JobCompletionCallback;
  private onFailed?: (jobId: string, error?: string) => void;

  constructor(
    pollInterval: number = 2000,
    onComplete?: JobCompletionCallback,
    onFailed?: (jobId: string, error?: string) => void,
  ) {
    this.pollInterval = pollInterval;
    this.onComplete = onComplete;
    this.onFailed = onFailed;
  }

  /**
   * Start polling job status
   */
  public async pollJobStatus(
    jobId: string,
    attempts: number = 0,
  ): Promise<void> {
    // Show running state on first call
    if (attempts === 0) {
      // Show pulsing dot
      const pulseDot = document.getElementById("progressPulseDot");
      if (pulseDot) pulseDot.style.display = "inline-block";

      // Update subtitle
      const subtitle = document.getElementById("progressSubtitle");
      if (subtitle) subtitle.textContent = "Processing your BibTeX file...";

      // Update status text
      updateElementText("progressStatus", "Starting enrichment...");
    }

    if (attempts > this.maxAttempts) {
      console.error("[BibTeX] Polling timeout after 180 attempts");
      this.handleTimeout();
      return;
    }

    try {
      const response = await fetch(
        `/scholar/api/bibtex/job/${jobId}/status/`,
      );
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const data: JobStatusResponse = await response.json();

      // Update UI with current status
      this.updateProgressUI(data);
      this.updateLogUI(data);

      // Check if done
      if (data.status === "completed") {
        this.handleCompletion(jobId);
      } else if (data.status === "failed") {
        this.handleFailure(jobId, data.error_message);
      } else {
        // Continue polling
        setTimeout(
          () => this.pollJobStatus(jobId, attempts + 1),
          this.pollInterval,
        );
      }
    } catch (error) {
      console.error("Polling error:", error);
      // Retry with longer delay on error
      setTimeout(
        () => this.pollJobStatus(jobId, attempts + 1),
        5000,
      );
    }
  }

  /**
   * Update progress UI elements
   */
  private updateProgressUI(data: JobStatusResponse): void {
    if (data.progress_percentage !== undefined) {
      const progressBar = document.getElementById("enrichmentProgressBar");
      if (progressBar) {
        progressBar.style.width = `${data.progress_percentage}%`;
      }
      updateElementText("progressPercent", `${data.progress_percentage}%`);
    }

    // Update status text
    if (data.total_papers !== undefined) {
      let statusText = `Processing ${data.processed_papers}/${data.total_papers} papers`;
      if (data.failed_papers && data.failed_papers > 0) {
        statusText += ` (${data.failed_papers} failed)`;
      }
      updateElementText("progressStatus", statusText);
    }
  }

  /**
   * Update log UI elements
   */
  private updateLogUI(data: JobStatusResponse): void {
    if (data.log) {
      // Update both processing log and enrichment log
      const logElements = [
        document.getElementById("processingLog"),
        document.getElementById("enrichmentProcessingLog"),
      ];

      logElements.forEach((element) => {
        if (element) {
          element.textContent = data.log || "";
          scrollToBottom(element.id);
        }
      });
    }
  }

  /**
   * Handle job completion
   */
  private handleCompletion(jobId: string): void {
    console.log("[BibTeX] Job completed! Setting up download...");

    // Hide pulsing dot
    const pulseDot = document.getElementById("progressPulseDot");
    if (pulseDot) pulseDot.style.display = "none";

    // Update subtitle to show completion
    const subtitle = document.getElementById("progressSubtitle");
    if (subtitle) subtitle.textContent = "Enrichment complete!";

    // Update status
    updateElementText("progressStatus", "Done");

    // Enable action buttons
    this.enableActionButtons(jobId);

    // Fetch and update URL count
    this.updateUrlCount(jobId);

    // Refresh workspace tree and expand bib_files directory
    this.refreshWorkspaceTree();

    // Notify callback
    if (this.onComplete) {
      this.onComplete(jobId);
    }
  }

  /**
   * Refresh workspace tree and expand bib_files directory
   */
  private async refreshWorkspaceTree(): Promise<void> {
    try {
      const tree = (window as any).scholarWorkspaceTree;
      if (tree && typeof tree.refreshAndExpandPath === "function") {
        console.log("[BibTeX] Refreshing workspace tree and expanding bib_files...");
        await tree.refreshAndExpandPath("scitex/scholar/bib_files");
      } else {
        console.warn("[BibTeX] Workspace tree not available for refresh");
      }
    } catch (error) {
      console.error("[BibTeX] Failed to refresh workspace tree:", error);
      // Don't fail the completion if tree refresh fails
    }
  }

  /**
   * Enable action buttons after completion
   */
  private enableActionButtons(jobId: string): void {
    // Enable download button
    const downloadBtn = document.getElementById(
      "downloadBtn",
    ) as HTMLButtonElement | null;
    if (downloadBtn) {
      setButtonState("downloadBtn", true);
      downloadBtn.onclick = () => {
        const downloadUrl = `/scholar/api/bibtex/job/${jobId}/download/`;
        (window as any).autoDownloadBibtexFile?.(downloadUrl);
      };
    }

    // Enable other buttons
    setButtonState("saveToProjectBtn", true);
    setButtonState("viewChangesBtn", true);
    setButtonState("showDiffBtn", true);
    setButtonState("openUrlsBtn", true);
    setButtonState("openUrlsMainBtn", true);
  }

  /**
   * Update URL count for "Open All URLs" buttons
   */
  private async updateUrlCount(jobId: string): Promise<void> {
    try {
      const response = await fetch(`/scholar/api/bibtex/job/${jobId}/urls/`);
      const urlData = await response.json();
      const count = urlData.total_urls || 0;

      // Update sidebar button count
      updateElementText("urlCount", count.toString());

      // Update main button text
      const urlButtonText = document.getElementById("urlButtonText");
      if (urlButtonText && count > 0) {
        urlButtonText.textContent = `Open All ${count} URLs`;
      }
    } catch (error) {
      console.error("[BibTeX] Failed to fetch URL count:", error);
      updateElementText("urlCount", "?");
    }
  }

  /**
   * Handle job failure
   */
  private handleFailure(jobId: string, errorMessage?: string): void {
    console.log("[BibTeX] Job failed:", errorMessage);

    const errorMsg = "\n\n✗ ERROR: " + (errorMessage || "Unknown error");

    // Update logs
    const logElements = [
      document.getElementById("processingLog"),
      document.getElementById("enrichmentProcessingLog"),
    ];

    logElements.forEach((element) => {
      if (element) {
        element.textContent += errorMsg;
      }
    });

    // Hide running indicator after delay
    setTimeout(() => {
      setElementVisibility("enrichmentRunningIndicator", false);
      // Optionally reset form
    }, 5000);

    // Notify callback
    if (this.onFailed) {
      this.onFailed(jobId, errorMessage);
    }
  }

  /**
   * Handle polling timeout
   */
  private handleTimeout(): void {
    const errorMsg = "\n\n✗ Polling timeout. Please refresh the page.";

    const logElements = [
      document.getElementById("processingLog"),
      document.getElementById("enrichmentProcessingLog"),
    ];

    logElements.forEach((element) => {
      if (element) {
        element.textContent += errorMsg;
      }
    });
  }
}
