/**
 * BibTeX Enrichment Functionality
 *
 * Handles:
 * - File upload and job submission
 * - Job status polling
 * - Download functionality
 * - URL opening
 * - Diff/comparison display
 *
 * @requires CSRF token in page
 * @requires URL endpoints configured
 */

// Global state
let jobStatusInterval = null;
window.currentBibtexJobId = null;

/**
 * Initialize BibTeX enrichment system
 * @param {Object} config - Configuration
 */
function initBibtexEnrichment(config = {}) {
  const {
    formId = "bibtexEnrichmentForm",
    fileInputId = "bibtexFileInput",
    uploadUrl = "/scholar/bibtex/upload/",
  } = config;

  const form = document.getElementById(formId);
  const fileInput = document.getElementById(fileInputId);

  if (!form || !fileInput) {
    console.warn("BibTeX enrichment form not found");
    return;
  }

  // File input change handler
  fileInput.addEventListener("change", handleFileSelect);

  // Form submit handler
  form.addEventListener("submit", handleFormSubmit);

  // Drag and drop support
  setupDragAndDrop();
}

/**
 * Handle file selection
 */
function handleFileSelect(e) {
  const file = e.target.files[0];
  if (!file) return;

  // Validate file type
  if (!file.name.endsWith(".bib")) {
    showNotification("Please select a .bib file", "error");
    e.target.value = "";
    return;
  }

  // Show file name in UI
  const fileName = file.name;
  console.log("Selected file:", fileName);

  // Update UI to show selected file
  const fileNameDisplay = document.getElementById("fileNameDisplay");
  const fileNameSpan = document.getElementById("fileName");
  if (fileNameDisplay && fileNameSpan) {
    fileNameSpan.textContent = fileName;
    fileNameDisplay.style.display = "block";
  }

  // Auto-submit the form to start enrichment
  const form = document.getElementById("bibtexEnrichmentForm");
  if (form) {
    console.log("Auto-submitting form for file:", fileName);
    form.dispatchEvent(
      new Event("submit", { bubbles: true, cancelable: true }),
    );
  }
}

/**
 * Handle form submission - Start enrichment directly
 */
function handleFormSubmit(e, forceCancel = false) {
  e.preventDefault();

  const formData = new FormData(e.target);
  const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]").value;

  // Add force_cancel flag if user confirmed cancellation
  if (forceCancel) {
    formData.append("force_cancel", "true");
  }

  // Start enrichment directly (no preview)
  startEnrichmentJob(e.target, formData, csrfToken, forceCancel);
}

/**
 * Show BibTeX preview before enrichment
 */
function showBibtexPreview(form, formData, csrfToken) {
  console.log("Showing BibTeX preview...");
  // Show loading state
  showLoadingState();

  fetch("/scholar/bibtex/preview/", {
    method: "POST",
    headers: {
      "X-Requested-With": "XMLHttpRequest",
      "X-CSRFToken": csrfToken,
    },
    body: formData,
  })
    .then((response) => response.json())
    .then((data) => {
      console.log("Preview data received:", data);
      if (data.success) {
        displayPreviewModal(data, form, formData, csrfToken);
        resetForm(); // Hide progress area
      } else {
        console.error("Preview failed:", data.error);
        showError(data.error || "Failed to preview file");
        resetForm();
      }
    })
    .catch((error) => {
      console.error("Preview error:", error);
      showError("Failed to preview file: " + error.message);
      resetForm();
    });
}

/**
 * Display preview modal
 */
function displayPreviewModal(data, form, formData, csrfToken) {
  // Create modal HTML
  const modal = document.createElement("div");
  modal.id = "bibtexPreviewModal";
  modal.style.cssText =
    "position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: var(--color-canvas-overlay, rgba(0, 0, 0, 0.95)); z-index: 9999; overflow: auto;";

  let entriesHtml = "";
  data.entries.forEach((entry) => {
    const statusIcons = [];
    if (entry.has_abstract)
      statusIcons.push(
        '<span style="color: var(--success-color);" title="Has abstract"><i class="fas fa-check-circle"></i> Abstract</span>',
      );
    if (entry.has_url)
      statusIcons.push(
        '<span style="color: var(--success-color);" title="Has URL/DOI"><i class="fas fa-check-circle"></i> URL</span>',
      );
    if (entry.has_citations)
      statusIcons.push(
        '<span style="color: var(--success-color);" title="Has citations"><i class="fas fa-check-circle"></i> Citations</span>',
      );

    const missingIcons = [];
    if (!entry.has_abstract)
      missingIcons.push(
        '<span style="color: var(--warning-color);" title="Missing abstract"><i class="fas fa-exclamation-circle"></i> Abstract</span>',
      );
    if (!entry.has_url)
      missingIcons.push(
        '<span style="color: var(--warning-color);" title="Missing URL/DOI"><i class="fas fa-exclamation-circle"></i> URL</span>',
      );
    if (!entry.has_citations)
      missingIcons.push(
        '<span style="color: var(--warning-color);" title="Missing citations"><i class="fas fa-exclamation-circle"></i> Citations</span>',
      );

    entriesHtml += `
            <div style="margin-bottom: 1rem; border: 1px solid var(--color-border-default); border-radius: 6px; padding: 1rem; background: var(--color-canvas-default);">
                <div style="font-weight: 700; color: var(--color-fg-default); margin-bottom: 0.5rem;">
                    <i class="fas fa-file-alt"></i> @${entry.type}{${escapeHtml(entry.key)}}
                </div>
                <div style="color: var(--color-fg-muted); font-size: 0.9rem; font-style: italic; margin-bottom: 0.5rem;">
                    "${escapeHtml(entry.title)}"
                </div>
                <div style="font-size: 0.85rem; color: var(--color-fg-muted); margin-bottom: 0.5rem;">
                    ${escapeHtml(entry.author)} (${escapeHtml(entry.year)})
                </div>
                <div style="display: flex; gap: 1rem; flex-wrap: wrap; font-size: 0.85rem;">
                    ${statusIcons.join("")}
                    ${missingIcons.join("")}
                </div>
            </div>
        `;
  });

  const limitWarning = data.showing_limited
    ? `
        <div style="background: var(--warning-color); color: var(--white); padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem;">
            <i class="fas fa-info-circle"></i> Showing first 50 entries. Total: ${data.total_entries} entries
        </div>
    `
    : "";

  modal.innerHTML = `
        <div style="max-width: 900px; margin: 2rem auto; background: var(--color-canvas-default); border: 1px solid var(--color-border-default); border-radius: 12px; padding: 2rem; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);">
            <button onclick="closePreviewModal()" style="float: right; background: transparent; border: none; font-size: 2rem; cursor: pointer; color: var(--color-fg-muted); line-height: 1;">
                ×
            </button>
            <h3 style="color: var(--color-fg-default); margin-bottom: 1rem; font-size: 1.5rem; font-weight: 700;">
                <i class="fas fa-eye"></i> Preview: ${escapeHtml(data.filename)}
            </h3>
            <p style="color: var(--color-fg-muted); margin-bottom: 1.5rem;">
                Found <strong style="color: var(--color-fg-default);">${data.total_entries}</strong> entries. Review them before starting enrichment.
            </p>
            ${limitWarning}
            <div style="max-height: 500px; overflow-y: auto; margin-bottom: 1.5rem; padding-right: 0.5rem;">
                ${entriesHtml}
            </div>
            <div style="display: flex; justify-content: space-between; gap: 1rem;">
                <button onclick="closePreviewModal()" style="padding: 1rem 2rem; background: var(--color-btn-bg); border: 1px solid var(--color-border-default); border-radius: 6px; cursor: pointer; color: var(--color-fg-default); font-weight: 600; transition: all 0.2s;">
                    <i class="fas fa-times"></i> Cancel
                </button>
                <button id="confirmEnrichmentBtn" style="padding: 1rem 2rem; background: var(--success-color); color: var(--white); border: none; border-radius: 6px; cursor: pointer; font-weight: 600; transition: all 0.2s;">
                    <i class="fas fa-check"></i> Start Enrichment
                </button>
            </div>
        </div>
    `;

  document.body.appendChild(modal);

  // Add event listener to confirm button
  document
    .getElementById("confirmEnrichmentBtn")
    .addEventListener("click", () => {
      console.log("User confirmed enrichment, starting job...");
      closePreviewModal();
      startEnrichmentJob(form, formData, csrfToken, false);
    });
}

/**
 * Close preview modal
 */
window.closePreviewModal = function () {
  const modal = document.getElementById("bibtexPreviewModal");
  if (modal) {
    modal.remove();
  }
};

/**
 * Start enrichment job (called after preview confirmation)
 */
function startEnrichmentJob(form, formData, csrfToken, forceCancel) {
  // Show loading state
  showLoadingState();

  fetch(form.action, {
    method: "POST",
    headers: {
      "X-Requested-With": "XMLHttpRequest",
      "X-CSRFToken": csrfToken,
    },
    body: formData,
  })
    .then((response) => {
      if (response.status === 409) {
        // Conflict - existing job found, requires confirmation
        return response.json().then((data) => {
          handleJobConflict(form, data, formData, csrfToken);
          throw new Error("Conflict handled");
        });
      }

      if (!response.ok) {
        // Server returned an error status (4xx, 5xx)
        return response.text().then((text) => {
          console.error(`Server error (${response.status}):`, text);
          throw new Error(
            `Upload failed: ${response.status} ${response.statusText}`,
          );
        });
      }

      return response.json();
    })
    .then((data) => {
      if (data.success) {
        window.currentBibtexJobId = data.job_id;
        // Store in localStorage for page reloads
        localStorage.setItem("currentBibtexJobId", data.job_id);
        console.log("Job started, ID saved to localStorage:", data.job_id);
        startJobPolling(data.job_id);
      } else {
        showError(data.error || "Upload failed");
        resetForm();
      }
    })
    .catch((error) => {
      if (error.message === "Conflict handled") {
        // This is expected, don't show error
        resetForm();
        return;
      }
      console.error("Upload error:", error);
      showError("Failed to upload file: " + error.message);
      resetForm();
    });
}

/**
 * Handle job conflict - ask user to cancel old job
 */
function handleJobConflict(form, data, formData, csrfToken) {
  const existingJob = data.existing_job;
  const message = `You already have a job in progress:\n"${existingJob.filename}"\nProgress: ${existingJob.progress}%\n\nCancel it and start new job?`;

  if (confirm(message)) {
    // User confirmed - resubmit with force_cancel flag
    formData.append("force_cancel", "true");
    startEnrichmentJob(form, formData, csrfToken, true);
  }
}

/**
 * Setup drag and drop
 */
function setupDragAndDrop() {
  const dropZone = document.getElementById("dropZone");
  if (!dropZone) return;

  ["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
    dropZone.addEventListener(eventName, preventDefaults, false);
  });

  function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
  }

  ["dragenter", "dragover"].forEach((eventName) => {
    dropZone.addEventListener(eventName, () => {
      dropZone.style.borderColor = "var(--scitex-color-03)";
      dropZone.style.background = "var(--color-canvas-subtle)";
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropZone.addEventListener(eventName, () => {
      dropZone.style.borderColor = "var(--scitex-color-03)";
      dropZone.style.background = "var(--color-canvas-default)";
    });
  });

  dropZone.addEventListener("drop", (e) => {
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      document.getElementById("bibtexFileInput").files = files;
      handleFileSelect({ target: { files } });
    }
  });
}

/**
 * Load and display all papers from job
 * @param {string} jobId - Job UUID
 */
function loadJobPapers(jobId) {
  console.log("Loading papers for job:", jobId);

  fetch(`/scholar/api/bibtex/job/${jobId}/papers/`)
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        console.log("Papers loaded:", data.total_papers);
        displayPapersPlaceholders(data.papers, data.status);
      } else {
        console.error("Failed to load papers:", data.error);
      }
    })
    .catch((error) => {
      console.error("Error loading papers:", error);
    });
}

/**
 * Display papers as placeholders
 * @param {Array} papers - Array of paper objects
 * @param {string} jobStatus - Current job status
 */
function displayPapersPlaceholders(papers, jobStatus) {
  const papersArea = document.getElementById("bibtexPapersArea");
  const papersContainer = document.getElementById("papersContainer");
  const papersCount = document.getElementById("papersCount");

  if (!papersArea || !papersContainer || !papersCount) return;

  // Show papers area
  papersArea.style.display = "block";
  papersCount.textContent = papers.length;

  // Generate HTML for all papers
  let html = "";
  papers.forEach((paper, index) => {
    const statusIcons = [];
    if (paper.has_abstract)
      statusIcons.push(
        '<span style="color: var(--success-color);" title="Has abstract"><i class="fas fa-check-circle"></i></span>',
      );
    else
      statusIcons.push(
        '<span style="color: var(--color-fg-muted);" title="No abstract"><i class="fas fa-circle"></i></span>',
      );

    if (paper.has_url)
      statusIcons.push(
        '<span style="color: var(--success-color);" title="Has URL/DOI"><i class="fas fa-check-circle"></i></span>',
      );
    else
      statusIcons.push(
        '<span style="color: var(--color-fg-muted);" title="No URL"><i class="fas fa-circle"></i></span>',
      );

    if (paper.has_citations)
      statusIcons.push(
        '<span style="color: var(--success-color);" title="Has citations"><i class="fas fa-check-circle"></i></span>',
      );
    else
      statusIcons.push(
        '<span style="color: var(--color-fg-muted);" title="No citations"><i class="fas fa-circle"></i></span>',
      );

    html += `
            <div class="paper-card" id="paper-${index}" style="margin-bottom: 0.75rem; border: 1px solid var(--color-border-default); border-radius: 6px; padding: 1rem; background: var(--color-canvas-default);">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.5rem;">
                    <div style="flex: 1;">
                        <div style="font-weight: 600; color: var(--color-fg-default); margin-bottom: 0.25rem;">
                            ${escapeHtml(paper.title || "No title")}
                        </div>
                        <div style="font-size: 0.85rem; color: var(--color-fg-muted);">
                            ${escapeHtml(paper.author || "Unknown")} (${escapeHtml(paper.year || "N/A")})
                        </div>
                        ${paper.journal ? `<div style="font-size: 0.8rem; color: var(--color-fg-muted); font-style: italic;">${escapeHtml(paper.journal)}</div>` : ""}
                    </div>
                    <div style="display: flex; gap: 0.5rem; font-size: 0.9rem; margin-left: 1rem;">
                        ${statusIcons.join("")}
                    </div>
                </div>
                ${
                  paper.abstract
                    ? `
                    <div style="font-size: 0.85rem; color: var(--color-fg-muted); margin-top: 0.5rem; padding-top: 0.5rem; border-top: 1px solid var(--color-border-default);">
                        <strong>Abstract:</strong> ${escapeHtml(paper.abstract.substring(0, 250))}${paper.abstract.length > 250 ? '... <span style="color: var(--color-fg-muted); font-style: italic;">(truncated)</span>' : ""}
                    </div>
                `
                    : ""
                }
            </div>
        `;
  });

  papersContainer.innerHTML = html;
}

/**
 * Start polling job status
 * @param {string} jobId - Job UUID
 */
function startJobPolling(jobId) {
  // Clear any existing interval
  if (jobStatusInterval) {
    clearInterval(jobStatusInterval);
  }

  // Load and display papers immediately
  loadJobPapers(jobId);

  // Show progress area (try both ID variants for compatibility)
  const progressArea =
    document.getElementById("bibtexProgressArea") ||
    document.getElementById("progressArea");
  if (progressArea) {
    progressArea.style.display = "block";
  }

  // Poll immediately, then every 2 seconds
  updateJobStatus(jobId);
  jobStatusInterval = setInterval(() => updateJobStatus(jobId), 2000);
}

/**
 * Update job status
 * @param {string} jobId - Job UUID
 */
function updateJobStatus(jobId) {
  fetch(`/scholar/api/bibtex/job/${jobId}/status/`)
    .then((response) => response.json())
    .then((data) => {
      updateProgressUI(data);

      // If completed or failed, stop polling
      if (data.status === "completed" || data.status === "failed") {
        stopJobPolling();
        handleJobComplete(data);
      }
    })
    .catch((error) => {
      console.error("Status check error:", error);
    });
}

/**
 * Stop job polling
 */
function stopJobPolling() {
  if (jobStatusInterval) {
    clearInterval(jobStatusInterval);
    jobStatusInterval = null;
  }
}

/**
 * Update progress UI
 * @param {Object} data - Job status data
 */
function updateProgressUI(data) {
  // Update old progress elements (for compatibility)
  const progressBar = document.getElementById("progressBar");
  const progressPercentage = document.getElementById("progressPercentage");
  const progressDetails = document.getElementById("progressDetails");
  const processingLog = document.getElementById("processingLog");

  if (progressBar) {
    progressBar.style.width = `${data.progress_percentage}%`;
  }

  if (progressPercentage) {
    progressPercentage.textContent = `${data.progress_percentage}%`;
  }

  if (progressDetails) {
    progressDetails.textContent = `${data.processed_papers}/${data.total_papers} papers processed`;
  }

  // Update new progress bar in running indicator
  const enrichmentProgressBar = document.getElementById(
    "enrichmentProgressBar",
  );
  const progressPercent = document.getElementById("progressPercent");
  const progressStatus = document.getElementById("progressStatus");

  if (enrichmentProgressBar) {
    enrichmentProgressBar.style.width = `${data.progress_percentage}%`;
  }

  if (progressPercent) {
    progressPercent.textContent = `${data.progress_percentage}%`;
  }

  if (progressStatus) {
    // Calculate ETA if we have progress data
    if (data.processed_papers > 0 && data.total_papers > 0) {
      const remaining = data.total_papers - data.processed_papers;

      // If we have timing data, calculate ETA
      if (data.elapsed_time && data.processed_papers > 0) {
        const avgTimePerPaper = data.elapsed_time / data.processed_papers;
        const estimatedRemainingTime = avgTimePerPaper * remaining;
        const etaSeconds = Math.ceil(estimatedRemainingTime);

        let etaText = "";
        if (etaSeconds < 60) {
          etaText = `ETA: ${etaSeconds}s`;
        } else if (etaSeconds < 3600) {
          const minutes = Math.floor(etaSeconds / 60);
          const seconds = etaSeconds % 60;
          etaText = `ETA: ${minutes}m ${seconds}s`;
        } else {
          const hours = Math.floor(etaSeconds / 3600);
          const minutes = Math.floor((etaSeconds % 3600) / 60);
          etaText = `ETA: ${hours}h ${minutes}m`;
        }

        progressStatus.textContent = `${data.processed_papers}/${data.total_papers} papers • ${etaText}`;
      } else {
        progressStatus.textContent = `Processing ${data.processed_papers}/${data.total_papers} papers`;
      }
    } else {
      progressStatus.textContent = data.status_message || "Processing...";
    }
  }

  if (processingLog && data.log) {
    processingLog.textContent = data.log;
    // Auto-scroll to bottom
    processingLog.scrollTop = processingLog.scrollHeight;
  }

  // Also update the enrichment processing log in the running indicator
  const enrichmentLog = document.getElementById("enrichmentProcessingLog");
  if (enrichmentLog && data.log) {
    enrichmentLog.textContent = data.log;
    // Auto-scroll to bottom
    enrichmentLog.scrollTop = enrichmentLog.scrollHeight;
  }
}

/**
 * Handle job completion
 * @param {Object} data - Job status data
 */
function handleJobComplete(data) {
  // Hide running indicator
  const runningIndicator = document.getElementById(
    "enrichmentRunningIndicator",
  );
  if (runningIndicator) {
    console.log(
      "Hiding enrichment running indicator - job status:",
      data.status,
    );
    runningIndicator.style.display = "none";
  }

  if (data.status === "completed" && data.has_output) {
    showDownloadArea(window.currentBibtexJobId);
  } else if (data.status === "failed") {
    showError(data.error_message || "Enrichment failed");
  }
}

/**
 * Enable download buttons
 * @param {string} jobId - Job UUID
 */
function showDownloadArea(jobId) {
  const downloadBtn = document.getElementById("downloadBtn");
  const showDiffBtn = document.getElementById("showDiffBtn");
  const openUrlsBtn = document.getElementById("openUrlsBtn");
  const saveToProjectBtn = document.getElementById("saveToProjectBtn");

  // Store job ID for download
  window.currentBibtexJobId = jobId;

  if (downloadBtn) {
    downloadBtn.disabled = false;
    downloadBtn.style.opacity = "1";
    downloadBtn.style.cursor = "pointer";
  }

  if (showDiffBtn) {
    showDiffBtn.disabled = false;
    showDiffBtn.style.opacity = "1";
    showDiffBtn.style.cursor = "pointer";
  }

  if (openUrlsBtn) {
    openUrlsBtn.disabled = false;
    openUrlsBtn.style.opacity = "1";
    openUrlsBtn.style.cursor = "pointer";
  }

  if (saveToProjectBtn) {
    saveToProjectBtn.disabled = false;
    saveToProjectBtn.style.opacity = "1";
    saveToProjectBtn.style.cursor = "pointer";
  }

  // Fetch URL count for "Open All URLs" button
  if (openUrlsBtn) {
    fetch(`/scholar/api/bibtex/job/${jobId}/urls/`)
      .then((response) => response.json())
      .then((data) => {
        if (data.total_urls > 0) {
          document.getElementById("urlCount").textContent = data.total_urls;
        }
      });
  }
}

/**
 * Open all paper URLs
 */
window.openAllPaperUrls = function () {
  const jobId = window.currentBibtexJobId;
  if (!jobId) {
    showNotification("No job ID available.", "error");
    return;
  }

  fetch(`/scholar/api/bibtex/job/${jobId}/urls/`)
    .then((response) => response.json())
    .then((data) => {
      if (!data.urls || data.urls.length === 0) {
        showNotification("No URLs found in the enriched BibTeX file.", "info");
        return;
      }

      if (
        !confirm(
          `Open ${data.total_urls} URLs in new tabs?\n\nNote: Your browser may block some tabs.`,
        )
      ) {
        return;
      }

      // Open URLs with staggered delay
      data.urls.forEach((item, index) => {
        setTimeout(() => {
          window.open(item.url, "_blank");
        }, index * 100);
      });
    })
    .catch((error) => {
      console.error("Error fetching URLs:", error);
      showNotification("Failed to fetch URLs.", "error");
    });
};

/**
 * Show BibTeX diff
 */
window.showBibtexDiff = function () {
  const jobId = window.currentBibtexJobId;
  if (!jobId) {
    showNotification("No job ID available.", "error");
    return;
  }

  // Show modal
  const modal = document.getElementById("bibtexDiffModal");
  const content = document.getElementById("bibtexDiffContent");

  if (modal) modal.style.display = "block";
  if (content) content.innerHTML = "Loading comparison...";

  // Fetch diff
  fetch(`/scholar/api/bibtex/job/${jobId}/diff/`)
    .then((response) => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    })
    .then((data) => {
      if (data.success) {
        displayBibtexDiff(data.diff, data.stats);
      } else {
        if (content) {
          content.innerHTML = `<div style="color: var(--error-color);">Error: ${data.error || "Failed to generate diff"}</div>`;
        }
      }
    })
    .catch((error) => {
      console.error("Diff error:", error);
      if (content) {
        content.innerHTML = `<div style="color: var(--error-color);">Failed to load comparison: ${error.message}</div>`;
      }
    });
};

/**
 * Close BibTeX diff modal
 */
window.closeBibtexDiff = function () {
  const modal = document.getElementById("bibtexDiffModal");
  if (modal) modal.style.display = "none";
};

/**
 * Display BibTeX diff
 * @param {Array} diffData - Diff entries
 * @param {Object} stats - Statistics
 */
function displayBibtexDiff(diffData, stats) {
  let html = "";

  // Statistics dashboard
  if (stats) {
    html += `
            <div style="background: var(--color-canvas-subtle); padding: 1.5rem; border-radius: 8px; margin-bottom: 2rem; border-left: 4px solid var(--success-color);">
                <h3 style="color: var(--color-fg-default); margin-bottom: 1rem; font-size: 1.2rem;">
                    <i class="fas fa-chart-bar"></i> Enhancement Statistics
                </h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">
                    <div style="text-align: center;">
                        <div style="color: var(--color-fg-muted); font-size: 0.85rem;">Total Entries</div>
                        <div style="color: var(--scitex-color-03); font-size: 1.8rem; font-weight: 700;">${stats.total_entries}</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="color: var(--color-fg-muted); font-size: 0.85rem;">Entries Enhanced</div>
                        <div style="color: var(--success-color); font-size: 1.8rem; font-weight: 700;">${stats.entries_enhanced}</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="color: var(--color-fg-muted); font-size: 0.85rem;">Fields Added</div>
                        <div style="color: var(--success-color); font-size: 1.8rem; font-weight: 700;">${stats.total_fields_added}</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="color: var(--color-fg-muted); font-size: 0.85rem;">Fields Modified</div>
                        <div style="color: var(--warning-color); font-size: 1.8rem; font-weight: 700;">${stats.total_fields_modified}</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="color: var(--color-fg-muted); font-size: 0.85rem;">Enhancement Rate</div>
                        <div style="color: var(--scitex-color-02); font-size: 1.8rem; font-weight: 700;">${stats.enhancement_rate}%</div>
                    </div>
                </div>
            </div>
        `;
  }

  // No changes case
  if (!diffData || diffData.length === 0) {
    html += `
            <div style="text-align: center; padding: 3rem; color: var(--color-fg-muted);">
                <i class="fas fa-check-circle" style="font-size: 3rem; margin-bottom: 1rem; display: block;"></i>
                <p style="font-size: 1.1rem;">All entries are already complete!</p>
                <p style="font-size: 0.9rem;">No new fields were added during enrichment.</p>
            </div>
        `;
    document.getElementById("bibtexDiffContent").innerHTML = html;
    return;
  }

  // Display each entry with changes
  diffData.forEach((entry) => {
    html += renderDiffEntry(entry);
  });

  document.getElementById("bibtexDiffContent").innerHTML = html;
}

/**
 * Render a single diff entry
 * @param {Object} entry - Diff entry
 * @returns {string} HTML
 */
function renderDiffEntry(entry) {
  let html = `
        <div style="margin-bottom: 2rem; border: 1px solid var(--color-border-default); border-radius: 6px; padding: 1rem; background: var(--color-canvas-default);">
            <div style="font-weight: 700; font-size: 1.1rem; color: var(--color-fg-default); margin-bottom: 0.75rem;">
                <i class="fas fa-file-alt"></i> @${entry.type}{${entry.key}}
            </div>
    `;

  // Title
  if (entry.title) {
    const shortTitle =
      entry.title.length > 100
        ? entry.title.substring(0, 100) + "..."
        : entry.title;
    html += `
            <div style="color: var(--color-fg-muted); font-size: 0.9rem; margin-bottom: 0.75rem; font-style: italic;">
                "${escapeHtml(shortTitle)}"
            </div>
        `;
  }

  // Added fields
  if (entry.added_fields && Object.keys(entry.added_fields).length > 0) {
    html += `
            <div style="margin-top: 0.75rem; margin-bottom: 0.5rem; color: var(--success-color); font-weight: 600;">
                <i class="fas fa-plus-circle"></i> Added fields (${Object.keys(entry.added_fields).length}):
            </div>
        `;
    for (const [key, value] of Object.entries(entry.added_fields)) {
      const displayValue =
        value.length > 100 ? value.substring(0, 100) + "..." : value;
      html += `
                <div style="padding-left: 1.5rem; color: var(--success-color); margin-bottom: 0.25rem;">
                    <span style="font-weight: 600; background: var(--color-canvas-subtle); padding: 0.15rem 0.4rem; border-radius: 3px;">${escapeHtml(key)}</span> =
                    <span style="font-family: monospace;">{${escapeHtml(displayValue)}}</span>
                </div>
            `;
    }
  }

  // Modified fields
  if (entry.modified_fields && Object.keys(entry.modified_fields).length > 0) {
    html += `
            <div style="margin-top: 0.75rem; margin-bottom: 0.5rem; color: var(--warning-color); font-weight: 600;">
                <i class="fas fa-edit"></i> Modified fields (${Object.keys(entry.modified_fields).length}):
            </div>
        `;
    for (const [key, change] of Object.entries(entry.modified_fields)) {
      const oldValue =
        change.old.length > 50
          ? change.old.substring(0, 50) + "..."
          : change.old;
      const newValue =
        change.new.length > 50
          ? change.new.substring(0, 50) + "..."
          : change.new;
      html += `
                <div style="padding-left: 1.5rem; margin-bottom: 0.5rem;">
                    <div style="font-weight: 600; background: var(--color-canvas-subtle); padding: 0.15rem 0.4rem; border-radius: 3px; display: inline-block; margin-bottom: 0.25rem;">
                        ${escapeHtml(key)}
                    </div>
                    <div style="padding-left: 0.5rem; color: var(--error-color); text-decoration: line-through; font-family: monospace; font-size: 0.85rem;">
                        - {${escapeHtml(oldValue)}}
                    </div>
                    <div style="padding-left: 0.5rem; color: var(--success-color); font-family: monospace; font-size: 0.85rem;">
                        + {${escapeHtml(newValue)}}
                    </div>
                </div>
            `;
    }
  }

  html += `</div>`;
  return html;
}

/**
 * Show loading state
 */
function showLoadingState() {
  const progressArea =
    document.getElementById("bibtexProgressArea") ||
    document.getElementById("progressArea");
  if (progressArea) {
    progressArea.style.display = "block";
  }

  // Show running indicator
  const runningIndicator = document.getElementById(
    "enrichmentRunningIndicator",
  );
  if (runningIndicator) {
    console.log("Showing enrichment running indicator");
    runningIndicator.style.display = "block";
  } else {
    console.warn("Running indicator element not found");
  }
}

/**
 * Reset form
 */
function resetForm() {
  const progressArea =
    document.getElementById("bibtexProgressArea") ||
    document.getElementById("progressArea");
  if (progressArea) {
    progressArea.style.display = "none";
  }

  // Hide running indicator
  const runningIndicator = document.getElementById(
    "enrichmentRunningIndicator",
  );
  if (runningIndicator) {
    console.log("Hiding enrichment running indicator - reset form");
    runningIndicator.style.display = "none";
  }
}

/**
 * Show notification toast
 * @param {string} message - Notification message
 * @param {string} type - Type: 'success', 'error', or 'info'
 */
function showNotification(message, type = "info") {
  const notification = document.createElement("div");
  notification.className = `notification notification-${type}`;
  notification.textContent = message;
  notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 24px;
        background: ${type === "success" ? "#1a7f16" : type === "error" ? "#da3633" : "#0969da"};
        color: white;
        border-radius: 6px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        z-index: 10000;
        font-size: 14px;
        animation: slideIn 0.3s ease;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    `;

  document.body.appendChild(notification);

  setTimeout(() => {
    notification.style.animation = "slideOut 0.3s ease";
    setTimeout(() => notification.remove(), 300);
  }, 3000);
}

/**
 * Show error (convenience wrapper for showNotification)
 * @param {string} message - Error message
 */
function showError(message) {
  showNotification(message, "error");
}

/**
 * Handle Save to Project button click - shows project selector modal
 */
window.handleSaveToProject = function () {
  const jobId = window.currentBibtexJobId;

  if (!jobId) {
    showNotification("No job available to save", "error");
    return;
  }

  // Show the project selector modal
  const modal = document.getElementById("projectSelectorModal");
  if (modal) {
    modal.style.display = "flex";
  }
};

/**
 * Close project selector modal
 */
window.closeProjectSelectorModal = function () {
  const modal = document.getElementById("projectSelectorModal");
  if (modal) {
    modal.style.display = "none";
  }
};

/**
 * Confirm project selection and save
 */
window.confirmProjectSelection = function () {
  const dropdown = document.getElementById("projectSelectorDropdown");
  const projectSelector = document.getElementById("projectSelector");
  const jobId = window.currentBibtexJobId;

  if (dropdown && dropdown.value) {
    // Update hidden input with selected project
    if (projectSelector) {
      projectSelector.value = dropdown.value;
    }

    console.log("Saving job", jobId, "to project", dropdown.value);

    // Close modal
    closeProjectSelectorModal();

    // Call save to project API endpoint with the selected project
    const originalValue = projectSelector ? projectSelector.value : null;
    if (projectSelector) {
      projectSelector.value = dropdown.value;
    }
    saveJobToProject(jobId);
    if (projectSelector && originalValue !== dropdown.value) {
      projectSelector.value = originalValue; // Restore original in case of error
    }
  } else {
    showNotification("Please select a project", "error");
  }
};

/**
 * Toggle processing log visibility
 */
window.toggleProcessingLogVisibility = function () {
  const log = document.getElementById("enrichmentProcessingLog");
  const icon = document.getElementById("logToggleIcon");

  if (log && icon) {
    if (log.style.display === "none") {
      log.style.display = "block";
      icon.className = "fas fa-chevron-down";
    } else {
      log.style.display = "none";
      icon.className = "fas fa-chevron-up";
    }
  }
};

/**
 * Show API documentation modal
 */
window.showApiDocumentation = function () {
  console.log("Showing API documentation...");

  const modal = document.createElement("div");
  modal.id = "apiDocModal";
  modal.style.cssText =
    "position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: var(--color-canvas-overlay, rgba(0, 0, 0, 0.95)); z-index: 9999; overflow: auto;";

  modal.innerHTML = `
        <div style="max-width: 900px; margin: 2rem auto; background: var(--color-canvas-default); border: 1px solid var(--color-border-default); border-radius: 12px; padding: 2rem; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);">
            <button onclick="closeApiDocumentation()" style="float: right; background: transparent; border: none; font-size: 2rem; cursor: pointer; color: var(--color-fg-muted); line-height: 1;">×</button>
            <h3 style="color: var(--color-fg-default); margin-bottom: 1rem; font-size: 1.5rem; font-weight: 700;">
                <i class="fas fa-book"></i> Scholar API Documentation
            </h3>

            <div style="color: var(--color-fg-muted); line-height: 1.6;">
                <h4 style="color: var(--color-fg-default); margin-top: 1.5rem; margin-bottom: 0.75rem;">CLI (Recommended)</h4>
                <pre style="background: var(--color-canvas-subtle); padding: 1rem; border-radius: 6px; overflow-x: auto; border: 1px solid var(--color-border-default);"><code style="color: var(--color-fg-default); font-family: monospace;">scitex cloud enrich -i orig.bib -o enriched.bib -a $SCITEX_API_KEY</code></pre>

                <h4 style="color: var(--color-fg-default); margin-top: 1.5rem; margin-bottom: 0.75rem;">Direct API</h4>

                <div style="margin-bottom: 1.5rem;">
                    <h5 style="color: var(--scitex-color-03); margin-bottom: 0.5rem;">POST /scholar/bibtex/preview/</h5>
                    <p style="margin-bottom: 0.5rem;">Preview BibTeX file contents before enrichment</p>
                    <pre style="background: var(--color-canvas-subtle); padding: 1rem; border-radius: 6px; overflow-x: auto; border: 1px solid var(--color-border-default);"><code style="color: var(--color-fg-default); font-family: monospace;">curl -X POST https://scitex.cloud/scholar/bibtex/preview/ \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -F "bibtex_file=@references.bib"</code></pre>
                </div>

                <div style="margin-bottom: 1.5rem;">
                    <h5 style="color: var(--scitex-color-03); margin-bottom: 0.5rem;">POST /scholar/bibtex/upload/</h5>
                    <p style="margin-bottom: 0.5rem;">Upload and start enrichment job</p>
                    <pre style="background: var(--color-canvas-subtle); padding: 1rem; border-radius: 6px; overflow-x: auto; border: 1px solid var(--color-border-default);"><code style="color: var(--color-fg-default); font-family: monospace;">curl -X POST https://scitex.cloud/scholar/bibtex/upload/ \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -F "bibtex_file=@references.bib" \\
  -F "num_workers=4"</code></pre>
                </div>

                <div style="margin-bottom: 1.5rem;">
                    <h5 style="color: var(--scitex-color-03); margin-bottom: 0.5rem;">GET /scholar/api/bibtex/job/{job_id}/status/</h5>
                    <p style="margin-bottom: 0.5rem;">Check job status and progress</p>
                    <pre style="background: var(--color-canvas-subtle); padding: 1rem; border-radius: 6px; overflow-x: auto; border: 1px solid var(--color-border-default);"><code style="color: var(--color-fg-default); font-family: monospace;">curl https://scitex.cloud/scholar/api/bibtex/job/{job_id}/status/ \\
  -H "Authorization: Bearer YOUR_API_KEY"</code></pre>
                </div>

                <div style="margin-bottom: 1.5rem;">
                    <h5 style="color: var(--scitex-color-03); margin-bottom: 0.5rem;">GET /scholar/api/bibtex/job/{job_id}/download/</h5>
                    <p style="margin-bottom: 0.5rem;">Download enriched BibTeX file</p>
                    <pre style="background: var(--color-canvas-subtle); padding: 1rem; border-radius: 6px; overflow-x: auto; border: 1px solid var(--color-border-default);"><code style="color: var(--color-fg-default); font-family: monospace;">curl https://scitex.cloud/scholar/api/bibtex/job/{job_id}/download/ \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -o enriched.bib</code></pre>
                </div>

                <h4 style="color: var(--color-fg-default); margin-top: 1.5rem; margin-bottom: 0.75rem;">Response Format</h4>
                <p>All API responses are in JSON format:</p>
                <pre style="background: var(--color-canvas-subtle); padding: 1rem; border-radius: 6px; overflow-x: auto; border: 1px solid var(--color-border-default);"><code style="color: var(--color-fg-default); font-family: monospace;">{
  "success": true,
  "job_id": "uuid-string",
  "message": "Job started"
}</code></pre>

                <div style="margin-top: 2rem; padding: 1rem; background: var(--color-canvas-subtle); border-left: 4px solid var(--scitex-color-02); border-radius: 6px;">
                    <p style="margin: 0;"><strong style="color: var(--color-fg-default);"><i class="fas fa-info-circle"></i> Note:</strong> Rate limits apply based on your subscription tier. Check your <a href="/scholar/api-keys/" style="color: var(--scitex-color-02);">API settings</a> for details.</p>
                </div>
            </div>
        </div>
    `;

  document.body.appendChild(modal);
};

/**
 * Close API documentation modal
 */
window.closeApiDocumentation = function () {
  const modal = document.getElementById("apiDocModal");
  if (modal) modal.remove();
};

/**
 * Toggle advanced options panel
 */
window.toggleAdvancedOptions = function () {
  const panel = document.getElementById("advancedOptionsPanel");
  const icon = document.getElementById("advancedOptionsIcon");

  if (!panel || !icon) return;

  if (panel.style.display === "none") {
    panel.style.display = "block";
    icon.className = "fas fa-chevron-up";
    console.log("Advanced options expanded");
  } else {
    panel.style.display = "none";
    icon.className = "fas fa-chevron-down";
    console.log("Advanced options collapsed");
  }
};

/**
 * Toggle jobs history visibility
 */
window.toggleJobsHistory = function () {
  const container = document.getElementById("recentJobsContainer");
  const icon = document.getElementById("toggleJobsHistoryIcon");
  const text = document.getElementById("toggleJobsHistoryText");

  if (!container || !icon || !text) return;

  if (container.style.display === "none") {
    container.style.display = "block";
    icon.className = "fas fa-chevron-up";
    text.textContent = "Hide";
    console.log("Jobs history expanded");
  } else {
    container.style.display = "none";
    icon.className = "fas fa-chevron-down";
    text.textContent = "Show";
    console.log("Jobs history collapsed");
  }
};

/**
 * Escape HTML
 * @param {string} text - Text to escape
 * @returns {string} Escaped text
 */
function escapeHtml(text) {
  const map = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  };
  return String(text).replace(/[&<>"']/g, (m) => map[m]);
}

// Cleanup on page unload
window.addEventListener("beforeunload", () => {
  stopJobPolling();
});

/**
 * Load and display recent jobs history
 */
function loadRecentJobs() {
  console.log("Loading recent jobs history...");

  fetch("/scholar/api/bibtex/recent-jobs/")
    .then((response) => response.json())
    .then((data) => {
      if (data.success && data.jobs.length > 0) {
        console.log("Recent jobs loaded:", data.total);
        displayRecentJobs(data.jobs);
      } else {
        console.log("No recent jobs found");
      }
    })
    .catch((error) => {
      console.error("Error loading recent jobs:", error);
    });
}

/**
 * Display recent jobs in the sidebar
 * @param {Array} jobs - Array of job objects
 */
function displayRecentJobs(jobs) {
  const recentJobsContainer = document.getElementById("recentJobsContainer");
  const noJobsMessage = document.getElementById("noRecentJobsMessage");

  if (!recentJobsContainer) return;

  // Hide/show the no jobs message
  if (noJobsMessage) {
    noJobsMessage.style.display = jobs.length === 0 ? "block" : "none";
  }

  // Set container to horizontal layout
  recentJobsContainer.style.display = "flex";
  recentJobsContainer.style.flexDirection = "row";
  recentJobsContainer.style.gap = "0.75rem";
  recentJobsContainer.style.overflowX = "auto";
  recentJobsContainer.style.paddingBottom = "0.5rem";

  // Generate HTML for recent jobs
  let html = "";
  jobs.forEach((job, index) => {
    const statusColor =
      {
        completed: "var(--success-color)",
        processing: "var(--scitex-color-03)",
        pending: "var(--warning-color)",
        failed: "var(--error-color)",
        cancelled: "var(--color-fg-muted)",
      }[job.status] || "var(--color-fg-default)";

    const statusIcon =
      {
        completed: "fa-check-circle",
        processing: "fa-spinner fa-spin",
        pending: "fa-hourglass-half",
        failed: "fa-times-circle",
        cancelled: "fa-ban",
      }[job.status] || "fa-circle";

    const date = new Date(job.created_at);
    const dateStr =
      date.toLocaleDateString() +
      " " +
      date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

    const isActive = window.currentBibtexJobId === job.id;
    const activeStyle = isActive
      ? "border-color: var(--scitex-color-03); background: var(--color-canvas-subtle);"
      : "";

    // Determine badge background color based on status
    const badgeColor =
      job.status === "completed"
        ? "var(--success-color)"
        : job.status === "processing"
          ? "var(--scitex-color-03)"
          : job.status === "pending"
            ? "var(--warning-color)"
            : job.status === "failed"
              ? "var(--error-color)"
              : job.status === "cancelled"
                ? "var(--error-color)"
                : "var(--color-fg-muted)";

    const badgeTextColor =
      job.status === "failed" || job.status === "cancelled" ? "white" : "white";

    html += `
            <div class="recent-job-card" data-job-id="${job.id}" style="flex: 0 0 auto; min-width: 200px; max-width: 240px; border-top: 4px solid ${statusColor}; padding: 0.75rem; background: var(--color-canvas-subtle); border-radius: 4px; position: relative; display: flex; flex-direction: column; transition: all 0.2s ease; hover: box-shadow 0 4px 12px rgba(0,0,0,0.15);">
                <button class="remove-job-btn" onclick="removeJobCard('${job.id}')" style="position: absolute; top: 0.5rem; right: 0.5rem; background: transparent; border: none; color: var(--color-fg-muted); cursor: pointer; font-size: 1rem; padding: 0.25rem; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; border-radius: 4px; opacity: 0.5; transition: all 0.2s;" onmouseover="this.style.opacity='1'; this.style.background='var(--error-color)'; this.style.color='var(--white)';" onmouseout="this.style.opacity='0.5'; this.style.background='transparent'; this.style.color='var(--color-fg-muted)';" title="Remove from list">
                    <i class="fas fa-times"></i>
                </button>
                <div style="font-weight: 600; color: var(--color-fg-default); font-size: 0.85rem; margin-bottom: 0.5rem; display: flex; align-items: center; gap: 0.5rem; padding-right: 1.5rem; overflow: hidden;">
                    <i class="fas ${statusIcon}" style="color: ${statusColor}; font-size: 0.8rem; flex-shrink: 0;"></i>
                    <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${escapeHtml(job.original_filename)}">${escapeHtml(job.original_filename)}</span>
                </div>
                <div style="font-size: 0.7rem; color: var(--color-fg-muted); margin-bottom: 0.5rem;">
                    ${job.total_papers} papers
                </div>
                <div style="margin-bottom: auto;">
                    <span style="display: inline-block; padding: 0.35rem 0.5rem; border-radius: 3px; font-size: 0.65rem; font-weight: 600; background: ${badgeColor}; color: ${badgeTextColor}; text-transform: capitalize;">
                        ${job.status}
                    </span>
                </div>
                ${
                  job.status === "completed"
                    ? `
                    <div style="display: flex; gap: 0.35rem; margin-top: 0.5rem; flex-wrap: wrap;">
                        <button onclick="saveJobToProject('${job.id}')" style="flex: 1; min-width: 0; padding: 0.3rem 0.5rem; font-size: 0.7rem; margin: 0; background: var(--warning-color); color: white; border: none; border-radius: 3px; cursor: pointer; font-weight: 600; transition: all 0.2s ease; display: flex; align-items: center; justify-content: center; gap: 0.25rem;" title="Save to project" onmouseover="this.style.opacity='0.85'; this.style.transform='scale(1.05)';" onmouseout="this.style.opacity='1'; this.style.transform='scale(1)';">
                            <i class="fas fa-folder"></i>
                        </button>
                        <button onclick="downloadJob('${job.id}')" style="flex: 1; min-width: 0; padding: 0.3rem 0.5rem; font-size: 0.7rem; margin: 0; background: var(--success-color); color: white; border: none; border-radius: 3px; cursor: pointer; font-weight: 600; transition: all 0.2s ease; display: flex; align-items: center; justify-content: center; gap: 0.25rem;" title="Download" onmouseover="this.style.opacity='0.85'; this.style.transform='scale(1.05)';" onmouseout="this.style.opacity='1'; this.style.transform='scale(1)';">
                            <i class="fas fa-download"></i>
                        </button>
                    </div>
                `
                    : ""
                }
            </div>
        `;
  });

  recentJobsContainer.innerHTML = html;
}

/**
 * Handle download button click in main panel
 */
window.handleDownload = function () {
  if (window.currentBibtexJobId) {
    console.log("Downloading current job:", window.currentBibtexJobId);
    window.location.href = `/scholar/api/bibtex/job/${window.currentBibtexJobId}/download/`;
  }
};

/**
 * Download job enriched file from history card
 * @param {string} jobId - Job UUID
 */
window.downloadJob = function (jobId) {
  console.log("Downloading job:", jobId);
  window.location.href = `/scholar/api/bibtex/job/${jobId}/download/`;
};

/**
 * Remove job card from recent jobs list
 * @param {string} jobId - Job UUID to remove
 */
window.removeJobCard = function (jobId) {
  console.log("Removing job card:", jobId);

  // Find the card element
  const card = document.querySelector(
    `.recent-job-card[data-job-id="${jobId}"]`,
  );

  if (!card) {
    console.warn("Job card not found:", jobId);
    return;
  }

  // Add fade-out animation
  card.style.transition = "all 0.3s ease-out";
  card.style.opacity = "0";
  card.style.transform = "translateX(20px)";

  // Remove card after animation completes
  setTimeout(() => {
    card.remove();
    console.log("Job card removed from DOM:", jobId);

    // Check if there are any remaining job cards
    const remainingCards = document.querySelectorAll(".recent-job-card");
    if (remainingCards.length === 0) {
      // Show "no jobs" message
      const container = document.getElementById("recentJobsContainer");
      if (container) {
        container.innerHTML =
          '<div style="text-align: center; color: var(--color-fg-muted); padding: 1rem; font-size: 0.9rem;">No recent jobs</div>';
      }
    }
  }, 300);
};

/**
 * Save job to project (called from history card buttons)
 * @param {string} jobId - Job UUID
 */
window.saveJobToProject = function (jobId) {
  console.log("Saving job to project:", jobId);

  // Check if user is authenticated
  const isAuthenticated = document.body.dataset.userAuthenticated === "true";
  if (!isAuthenticated) {
    // Visitor user - guide them
    if (
      confirm(
        "To save to a project, you need to:\n\n" +
          "1. Create a free account\n" +
          "2. Sign in\n" +
          "3. Create a project\n\n" +
          "Note: You can download the enriched file without an account.\n\n" +
          "Would you like to sign up now?",
      )
    ) {
      window.location.href =
        "/auth/signup/?next=" + encodeURIComponent("/scholar/#bibtex");
    }
    return;
  }

  // Check if user has projects
  const projectSelector = document.getElementById("projectSelector");
  if (!projectSelector) {
    if (
      confirm(
        "Please create a project first to save bibliography files.\n\n" +
          "Would you like to create a new project now?",
      )
    ) {
      window.location.href =
        "/new/?next=" + encodeURIComponent("/scholar/#bibtex");
    }
    return;
  }

  // Get selected project
  const projectId = projectSelector.value;
  if (!projectId) {
    if (
      confirm(
        "Please select a project from the dropdown to save.\n\n" +
          "Or create a new project?",
      )
    ) {
      window.location.href =
        "/new/?next=" + encodeURIComponent("/scholar/#bibtex");
    }
    return;
  }

  // Save to project via API
  const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]").value;
  const formData = new FormData();
  formData.append("project_id", projectId);

  fetch(`/scholar/api/bibtex/job/${jobId}/save-to-project/`, {
    method: "POST",
    headers: {
      "X-CSRFToken": csrfToken,
    },
    body: formData,
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        // Redirect to show Django message alert
        window.location.reload();
      } else {
        // Show error message
        const message = data.error || "Failed to save to project";
        console.error("Save error:", message);
        showNotification(message, "error");
      }
    })
    .catch((error) => {
      console.error("Save error:", error);
      showNotification("Failed to save to project", "error");
    });
};

/**
 * Load most recent job on page load if exists
 */
function loadMostRecentJob() {
  // Check if there's a currentBibtexJobId in URL hash or local storage
  const urlHash = window.location.hash;
  const hashMatch = urlHash.match(/#bibtex-job-([0-9a-f-]+)/);

  if (hashMatch) {
    const jobId = hashMatch[1];
    console.log("Loading job from URL hash:", jobId);
    window.currentBibtexJobId = jobId;
    loadJobPapers(jobId);
    startJobPolling(jobId);
    return;
  }

  // Check localStorage for most recent job
  const recentJobId = localStorage.getItem("currentBibtexJobId");
  if (recentJobId) {
    console.log("Loading job from localStorage:", recentJobId);
    window.currentBibtexJobId = recentJobId;
    loadJobPapers(recentJobId);

    // Check status and start polling if needed
    fetch(`/scholar/api/bibtex/job/${recentJobId}/status/`)
      .then((response) => response.json())
      .then((data) => {
        if (data.status === "processing" || data.status === "pending") {
          startJobPolling(recentJobId);
        } else if (data.status === "completed") {
          // Show download buttons
          const progressArea = document.getElementById("bibtexProgressArea");
          if (progressArea) progressArea.style.display = "block";

          updateProgressUI(data);
          showDownloadArea(recentJobId);
        }
      })
      .catch((error) => {
        console.error("Error checking job status:", error);
      });
  }
}

// Auto-initialize when DOM is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    initBibtexEnrichment();
    loadRecentJobs(); // Load jobs history first
    loadMostRecentJob(); // Then load most recent job details
  });
} else {
  initBibtexEnrichment();
  loadRecentJobs();
  loadMostRecentJob();
}
