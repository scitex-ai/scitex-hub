/**

 * BibTeX Job Detail UI Module
 *
 * Handles UI interactions for the BibTeX job detail page including:
 * - Copy log to clipboard with visual feedback
 * - Expand/collapse log viewer
 * - Keyboard shortcuts for log selection
 * - Elapsed time tracking
 * - Real-time job status polling
 *
 * @module bibtex/job-detail-ui
 */

interface JobDetailElements {
  processingLog: HTMLPreElement | null;
  toggleLogSizeBtn: HTMLButtonElement | null;
  copyLogBtn: HTMLButtonElement | null;
  elapsedTimeEl: HTMLSpanElement | null;
}

/**
 * Copy log content to clipboard with visual feedback
 *
 * @param {HTMLButtonElement} button - The copy button element
 * @param {HTMLPreElement} logElement - The log content element
 */
async function copyLogToClipboard(
  button: HTMLButtonElement,
  logElement: HTMLPreElement,
): Promise<void> {
  console.log("[Job Detail UI] Attempting to copy log to clipboard");

  try {
    const logText = logElement.textContent || "";
    await navigator.clipboard.writeText(logText);

    console.log("[Job Detail UI] Log copied successfully");

    // Visual feedback - success
    const originalHTML = button.innerHTML;
    button.innerHTML = '<i class="fas fa-check"></i> Copied!';
    button.style.background = "var(--success-color)";
    button.style.color = "var(--white)";

    setTimeout(() => {
      button.innerHTML = originalHTML;
      button.style.background = "var(--color-btn-bg)";
      button.style.color = "var(--color-fg-default)";
    }, 2000);
  } catch (err) {
    console.error("[Job Detail UI] Failed to copy log:", err);

    // Fallback: select text for manual copy
    const range = document.createRange();
    range.selectNodeContents(logElement);
    const selection = window.getSelection();
    if (selection) {
      selection.removeAllRanges();
      selection.addRange(range);
    }

    // Show error feedback
    button.innerHTML =
      '<i class="fas fa-exclamation-triangle"></i> Select text manually';
    button.style.background = "var(--error-color)";
    button.style.color = "var(--white)";

    setTimeout(() => {
      button.innerHTML = '<i class="fas fa-copy"></i> Copy Log';
      button.style.background = "var(--color-btn-bg)";
      button.style.color = "var(--color-fg-default)";
    }, 3000);
  }
}

/**
 * Toggle log viewer size between compact and expanded
 *
 * @param {HTMLButtonElement} button - The toggle button element
 * @param {HTMLPreElement} logElement - The log content element
 * @param {boolean} expanded - Current expanded state
 * @returns {boolean} New expanded state
 */
function toggleLogSize(
  button: HTMLButtonElement,
  logElement: HTMLPreElement,
  expanded: boolean,
): boolean {
  console.log(
    "[Job Detail UI] Toggling log size, currently expanded:",
    expanded,
  );

  const newExpanded = !expanded;

  if (newExpanded) {
    logElement.style.maxHeight = "800px";
    button.innerHTML = '<i class="fas fa-compress-alt"></i>';
  } else {
    logElement.style.maxHeight = "400px";
    button.innerHTML = '<i class="fas fa-expand-alt"></i>';
  }

  return newExpanded;
}

/**
 * Handle Ctrl+A keyboard shortcut to select only log content
 *
 * @param {KeyboardEvent} event - The keyboard event
 * @param {HTMLPreElement} logElement - The log content element
 */
function handleLogKeyboardShortcut(
  event: KeyboardEvent,
  logElement: HTMLPreElement,
): void {
  // Check for Ctrl+A (Windows/Linux) or Cmd+A (Mac)
  if ((event.ctrlKey || event.metaKey) && event.key === "a") {
    console.log("[Job Detail UI] Ctrl+A detected, selecting log content");
    event.preventDefault();

    // Select all text in the log box
    const range = document.createRange();
    range.selectNodeContents(logElement);

    const selection = window.getSelection();
    if (selection) {
      selection.removeAllRanges();
      selection.addRange(range);
    }
  }
}

/**
 * Update elapsed time display
 *
 * @param {Date | null} startedAt - Job start timestamp
 * @param {HTMLElement} elapsedTimeEl - Element to update with elapsed time
 */
function updateElapsedTime(
  startedAt: Date | null,
  elapsedTimeEl: HTMLElement,
): void {
  if (!startedAt || !elapsedTimeEl) return;

  const now = new Date();
  const elapsedMs = now.getTime() - startedAt.getTime();
  const elapsedSec = Math.floor(elapsedMs / 1000);

  let display: string;

  if (elapsedSec < 60) {
    display = `${elapsedSec} seconds`;
  } else if (elapsedSec < 3600) {
    const minutes = Math.floor(elapsedSec / 60);
    const seconds = elapsedSec % 60;
    display = `${minutes}m ${seconds}s`;
  } else {
    const hours = Math.floor(elapsedSec / 3600);
    const minutes = Math.floor((elapsedSec % 3600) / 60);
    display = `${hours}h ${minutes}m`;
  }

  elapsedTimeEl.textContent = display;
}

/**
 * Poll job status and update UI in real-time
 *
 * @param {string} jobId - The job ID to poll
 * @param {string} jobStatus - Current job status
 * @param {HTMLPreElement | null} logElement - Log content element
 * @param {number} attempts - Current polling attempt number
 * @param {number} maxAttempts - Maximum polling attempts (default: 90)
 */
function pollJobStatus(
  jobId: string,
  jobStatus: string,
  logElement: HTMLPreElement | null,
  attempts: number = 0,
  maxAttempts: number = 90,
): void {
  console.log(`[POLL-SCHOLAR] Attempt ${attempts}, Job ID: ${jobId}`);

  if (attempts > maxAttempts) {
    console.error("[POLL-SCHOLAR] Timeout after", maxAttempts, "attempts");
    if (logElement) {
      logElement.textContent += "\n\n✗ Polling timeout after 3 minutes";
    }
    return;
  }

  fetch(`/apps/scholar/api/bibtex/job/${jobId}/status/`)
    .then((response) => {
      console.log(`[POLL-SCHOLAR] Response status: ${response.status}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      return response.json();
    })
    .then((data) => {
      console.log(
        `[POLL-SCHOLAR] Status: ${data.status}, Has log: ${!!data.log}, Log length: ${data.log ? data.log.length : 0}`,
      );

      // Update log immediately if available
      if (data.log && logElement) {
        logElement.textContent = data.log;
        // Auto-scroll to bottom
        logElement.scrollTop = logElement.scrollHeight;
        console.log(`[POLL-SCHOLAR] Updated log, length: ${data.log.length}`);
      } else {
        console.log("[POLL-SCHOLAR] No log in response");
      }

      // Update progress
      const progressBar = document.querySelector(
        '[style*="background: var(--scitex-color-03)"]',
      ) as HTMLElement;
      if (progressBar && data.progress_percentage !== undefined) {
        progressBar.style.width = `${data.progress_percentage}%`;
        console.log(`[POLL-SCHOLAR] Progress: ${data.progress_percentage}%`);
      }

      // Update paper counts
      const paperCount = document.querySelector(
        '[style*="color: var(--color-fg-muted)"]',
      );
      if (paperCount && data.total_papers !== undefined) {
        let text = `${data.processed_papers} / ${data.total_papers} papers processed`;
        if (data.failed_papers > 0) {
          text += ` (${data.failed_papers} failed)`;
        }
        paperCount.textContent = text;
      }

      // Update status
      if (data.status === "completed" || data.status === "failed") {
        console.log(`[POLL-SCHOLAR] Job ${data.status}, reloading page in 2s`);
        // Reload page to show final results
        setTimeout(() => location.reload(), 2000);
      } else {
        console.log("[POLL-SCHOLAR] Continuing polling...");
        // Continue polling
        setTimeout(
          () =>
            pollJobStatus(
              jobId,
              jobStatus,
              logElement,
              attempts + 1,
              maxAttempts,
            ),
          2000,
        );
      }
    })
    .catch((error) => {
      console.error(
        "[POLL-SCHOLAR] Error polling job status:",
        error.message || error,
      );

      // Display user-friendly error message in log
      if (logElement && attempts === 0) {
        logElement.textContent += `\n\n⚠ Connection error: ${error.message}. Retrying...`;
      }

      // Retry with exponential backoff (up to 10 seconds max)
      const backoffDelay = Math.min(5000 + attempts * 1000, 10000);
      setTimeout(
        () =>
          pollJobStatus(
            jobId,
            jobStatus,
            logElement,
            attempts + 1,
            maxAttempts,
          ),
        backoffDelay,
      );
    });
}

/**
 * Initialize job detail UI
 * Should be called from template with data-job-id attribute
 */
function initJobDetailUI(): void {
  console.log("[Job Detail UI] Initializing...");

  // Get job data from DOM
  const jobContainer = document.querySelector("[data-job-id]") as HTMLElement;
  if (!jobContainer) {
    console.log(
      "[Job Detail UI] No job container found, skipping initialization",
    );
    return;
  }

  const jobId = jobContainer.getAttribute("data-job-id");
  const jobStatus = jobContainer.getAttribute("data-job-status") || "";
  const startedAtStr = jobContainer.getAttribute("data-started-at");

  if (!jobId) {
    console.error("[Job Detail UI] No job ID found");
    return;
  }

  console.log("[Job Detail UI] Job ID:", jobId, "Status:", jobStatus);

  // Get elements
  const elements: JobDetailElements = {
    processingLog: document.getElementById("processing-log") as HTMLPreElement,
    toggleLogSizeBtn: document.getElementById(
      "toggle-log-size",
    ) as HTMLButtonElement,
    copyLogBtn: document.getElementById("copy-log-btn") as HTMLButtonElement,
    elapsedTimeEl: document.getElementById("elapsed-time") as HTMLSpanElement,
  };

  let logExpanded = false;

  // Copy log to clipboard
  if (elements.copyLogBtn && elements.processingLog) {
    elements.copyLogBtn.addEventListener("click", () => {
      copyLogToClipboard(elements.copyLogBtn!, elements.processingLog!);
    });
  }

  // Toggle log size
  if (elements.toggleLogSizeBtn && elements.processingLog) {
    elements.toggleLogSizeBtn.addEventListener("click", () => {
      logExpanded = toggleLogSize(
        elements.toggleLogSizeBtn!,
        elements.processingLog!,
        logExpanded,
      );
    });
  }

  // Handle Ctrl+A to select only log content
  if (elements.processingLog) {
    elements.processingLog.addEventListener("keydown", (e) => {
      handleLogKeyboardShortcut(e, elements.processingLog!);
    });

    // Make the log box focusable so it can receive keyboard events
    elements.processingLog.setAttribute("tabindex", "0");
  }

  // Update elapsed time
  const startedAt = startedAtStr ? new Date(startedAtStr) : null;
  let elapsedTimeInterval: number | null = null;

  function updateTime(): void {
    updateElapsedTime(startedAt, elements.elapsedTimeEl!);
  }

  if (jobStatus === "processing" || jobStatus === "pending") {
    elapsedTimeInterval = window.setInterval(updateTime, 1000);
  }
  updateTime(); // Initial update

  // Start polling only if job is not completed/failed
  if (jobStatus === "processing" || jobStatus === "pending") {
    pollJobStatus(jobId, jobStatus, elements.processingLog);
  }

  console.log("[Job Detail UI] Initialization complete");
}

// Initialize when DOM is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initJobDetailUI);
} else {
  initJobDetailUI();
}

// Export functions for external use if needed
export {
  initJobDetailUI,
  copyLogToClipboard,
  toggleLogSize,
  handleLogKeyboardShortcut,
  updateElapsedTime,
  pollJobStatus,
};
