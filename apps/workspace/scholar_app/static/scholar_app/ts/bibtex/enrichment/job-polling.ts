/**
 * Job Polling Module
 *
 * Handles BibTeX job status polling, progress updates, and log management.
 *
 * @module job-polling
 */
import { updateElementText, setElementVisibility, scrollToBottom, setButtonState, } from "./ui-utils";
/**
 * Job polling manager class
 */
export class JobPollingManager {
    constructor(pollInterval = 2000, onComplete, onFailed) {
        this.maxAttempts = 180;
        this.pollInterval = pollInterval;
        this.onComplete = onComplete;
        this.onFailed = onFailed;
    }
    /**
     * Start polling job status
     */
    async pollJobStatus(jobId, attempts = 0) {
        // Show running state on first call
        if (attempts === 0) {
            // Show pulsing dot
            const pulseDot = document.getElementById("progressPulseDot");
            if (pulseDot)
                pulseDot.style.display = "inline-block";
            // Update subtitle
            const subtitle = document.getElementById("progressSubtitle");
            if (subtitle)
                subtitle.textContent = "Processing your BibTeX file...";
            // Update status text
            updateElementText("progressStatus", "Starting enrichment...");
        }
        if (attempts > this.maxAttempts) {
            console.error("[BibTeX] Polling timeout after 180 attempts");
            this.handleTimeout();
            return;
        }
        try {
            const response = await fetch(`/apps/scholar/api/bibtex/job/${jobId}/status/`);
            if (!response.ok)
                throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            // Update UI with current status
            this.updateProgressUI(data);
            this.updateLogUI(data);
            // Check if done
            if (data.status === "completed") {
                this.handleCompletion(jobId);
            }
            else if (data.status === "failed") {
                this.handleFailure(jobId, data.error_message);
            }
            else {
                // Continue polling
                setTimeout(() => this.pollJobStatus(jobId, attempts + 1), this.pollInterval);
            }
        }
        catch (error) {
            console.error("Polling error:", error);
            // Retry with longer delay on error
            setTimeout(() => this.pollJobStatus(jobId, attempts + 1), 5000);
        }
    }
    /**
     * Update progress UI elements
     */
    updateProgressUI(data) {
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
    updateLogUI(data) {
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
    handleCompletion(jobId) {
        console.log("[BibTeX] Job completed! Setting up download...");
        // Hide pulsing dot
        const pulseDot = document.getElementById("progressPulseDot");
        if (pulseDot)
            pulseDot.style.display = "none";
        // Update subtitle to show completion
        const subtitle = document.getElementById("progressSubtitle");
        if (subtitle)
            subtitle.textContent = "Enrichment complete!";
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
    async refreshWorkspaceTree() {
        try {
            const tree = window.scholarWorkspaceTree;
            if (tree && typeof tree.refreshAndExpandPath === "function") {
                console.log("[BibTeX] Refreshing workspace tree and expanding bib_files...");
                await tree.refreshAndExpandPath("scitex/scholar/bib_files");
            }
            else {
                console.warn("[BibTeX] Workspace tree not available for refresh");
            }
        }
        catch (error) {
            console.error("[BibTeX] Failed to refresh workspace tree:", error);
            // Don't fail the completion if tree refresh fails
        }
    }
    /**
     * Enable action buttons after completion
     */
    enableActionButtons(jobId) {
        // Enable download button
        const downloadBtn = document.getElementById("downloadBtn");
        if (downloadBtn) {
            setButtonState("downloadBtn", true);
            downloadBtn.onclick = () => {
                const downloadUrl = `/apps/scholar/api/bibtex/job/${jobId}/download/`;
                window.autoDownloadBibtexFile?.(downloadUrl);
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
    async updateUrlCount(jobId) {
        try {
            const response = await fetch(`/apps/scholar/api/bibtex/job/${jobId}/urls/`);
            const urlData = await response.json();
            const count = urlData.total_urls || 0;
            // Update sidebar button count
            updateElementText("urlCount", count.toString());
            // Update main button text
            const urlButtonText = document.getElementById("urlButtonText");
            if (urlButtonText && count > 0) {
                urlButtonText.textContent = `Open All ${count} URLs`;
            }
        }
        catch (error) {
            console.error("[BibTeX] Failed to fetch URL count:", error);
            updateElementText("urlCount", "?");
        }
    }
    /**
     * Handle job failure
     */
    handleFailure(jobId, errorMessage) {
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
    handleTimeout() {
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
//# sourceMappingURL=job-polling.ts.map
