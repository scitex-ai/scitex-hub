/**
 * Job Actions Module
 *
 * Handles BibTeX job actions: download, open URLs, save to project.
 *
 * @module job-actions
 */

import { showConfirm } from "../../../../../../../static/shared/ts/components/confirm-modal.js";
import { showAlert, getCsrfToken, formatFileSize } from "./ui-utils.js";

/**
 * Auto-download BibTeX file when enrichment completes
 */
export async function autoDownloadBibtexFile(url: string): Promise<void> {
  console.log("[Auto-Download] Starting download for:", url);

  try {
    const response = await fetch(url);
    console.log("[Auto-Download] Response status:", response.status);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    // Extract filename from headers
    let filename = "enriched_bibliography.bib";
    const contentDisposition = response.headers.get("Content-Disposition");
    if (contentDisposition) {
      const match = contentDisposition.match(/filename="?(.+?)"?$/);
      if (match) filename = match[1];
    }
    console.log("[Auto-Download] Filename:", filename);

    const blob = await response.blob();
    const fileSizeMB = formatFileSize(blob.size);

    console.log("[Auto-Download] Creating download link...");
    const blobUrl = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = blobUrl;
    a.download = filename;
    a.style.display = "none";
    document.body.appendChild(a);
    a.click();

    setTimeout(() => {
      document.body.removeChild(a);
      window.URL.revokeObjectURL(blobUrl);
      console.log("[Auto-Download] ✓ Download completed");
    }, 100);

    // Success alert removed per user request
    // The download will happen silently in the browser
  } catch (error: any) {
    console.error("[Auto-Download] ✗ Failed:", error);

    // Show error alert with details
    showAlert(
      `❌ <strong>Download failed</strong><br><br>` +
        `${error.message || "Unknown error occurred"}<br><br>` +
        `Please try again or contact support if the problem persists.`,
      "error",
    );

    throw error; // Re-throw so caller can catch it
  }
}

/**
 * Open all paper URLs from enriched BibTeX file
 */
export async function openAllPaperUrls(jobId: string): Promise<void> {
  if (!jobId) {
    alert("No job ID available. Please wait for enrichment to complete.");
    return;
  }

  console.log("[Open URLs] Fetching URLs for job:", jobId);
  const urlsEndpoint = `/scholar/api/bibtex/job/${jobId}/urls/`;

  try {
    const response = await fetch(urlsEndpoint);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    console.log("[Open URLs] Received data:", data);

    if (data.urls && data.urls.length > 0) {
      showConfirm({
        title: `Open ${data.total_urls} paper URL(s) in new tabs?`,
        message: `This feature is useful when you want to download PDF files.\n\nWhat will happen:\n• Papers will open in background tabs\n• You can download PDF files efficiently\n\nPlease note:\n• Opening many tabs may clutter your browser\n• Your browser may block pop-ups - please allow them if needed`,
        confirmText: "Open All URLs",
        cancelText: "Cancel",
        onConfirm: () => {
          openUrlsInTabs(data.urls, jobId);
        },
      });
    } else {
      alert(
        "No URLs found in the enriched BibTeX file.\n\nThis could mean:\n- Papers don't have DOI or URL fields\n- Enrichment didn't add URLs\n- Try downloading the file to check",
      );
    }
  } catch (error: any) {
    console.error("[Open URLs] Error:", error);
    alert(
      `Failed to fetch URLs: ${error.message}\n\nPlease try downloading the BibTeX file manually.`,
    );
  }
}

/**
 * Open URLs in background tabs
 */
function openUrlsInTabs(urls: any[], jobId: string): void {
  console.log(`[Open URLs] Opening ${urls.length} URLs as tabs...`);

  let openedCount = 0;
  urls.forEach((paper: any, index: number) => {
    console.log(
      `[Open URLs] Opening: ${paper.title.substring(0, 50)}... (${paper.type})`,
    );
    // Use a unique target name for each tab so they all stay separate
    const targetName = `scitex_paper_${jobId}_${index}`;
    const tab = window.open(paper.url, targetName);
    if (tab) {
      // Immediately blur the new tab to keep focus on current page
      tab.blur();
      openedCount++;
    }
  });

  // Refocus on current window to stay here
  window.focus();

  // Show message about result
  if (openedCount === urls.length) {
    console.log(`[Open URLs] Successfully opened all ${openedCount} URLs`);
  } else if (openedCount > 0) {
    alert(
      `⚠️ Opened ${openedCount} out of ${urls.length} URLs.\n\nSome tabs were blocked by your browser's popup blocker.\nPlease allow popups for this site in your browser settings.`,
    );
  } else {
    alert(
      `❌ Could not open URLs.\n\nYour browser blocked the popups.\nPlease allow popups for this site:\n1. Click the blocked popup icon in your address bar\n2. Allow popups from this site\n3. Try again`,
    );
  }
}

/**
 * Save a job to the current/default project
 */
export async function saveJobToProject(jobId: string): Promise<void> {
  console.log("[Save to Project] Job ID:", jobId);

  // Get current project ID from hidden input or use default
  const projectInput = document.getElementById(
    "projectSelector",
  ) as HTMLInputElement;
  const projectId = projectInput?.value;

  console.log("[Save to Project] Project ID:", projectId);

  if (!projectId) {
    showAlert(
      "⚠ No project selected. Please select a project first.",
      "warning",
    );
    return;
  }

  const csrfToken = getCsrfToken();
  console.log(
    "[Save to Project] CSRF Token:",
    csrfToken ? "Present" : "Missing",
  );

  if (!csrfToken) {
    showAlert("CSRF token not found. Please refresh the page.", "error");
    return;
  }

  try {
    const response = await fetch(
      `/scholar/api/bibtex/job/${jobId}/save-to-project/`,
      {
        method: "POST",
        headers: {
          "X-CSRFToken": csrfToken,
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: `project_id=${encodeURIComponent(projectId)}`,
      },
    );

    console.log("[Save to Project] Response status:", response.status);

    const data = await response.json();
    console.log("[Save to Project] Response data:", data);

    if (response.ok && data.success) {
      const projectName = data.project || "project";

      // Build detailed success message with file paths
      let message = `✓ Successfully saved to <strong>${projectName}</strong>`;

      if (data.paths) {
        message += "<br><br><strong>Files saved:</strong><br>";
        if (data.paths.enriched) {
          message += `📄 <code>${data.paths.enriched}</code><br>`;
        }
        if (data.paths.merged && data.committed) {
          message += `📚 <code>${data.paths.merged}</code> (merged bibliography)`;
        }
      }

      if (data.committed) {
        message += "<br><br>✅ Auto-committed to Git repository";
      }

      showAlert(message, "success");
    } else {
      showAlert(
        `❌ Failed to save to project: ${data.error || "Unknown error"}`,
        "error",
      );
    }
  } catch (error: any) {
    console.error("[Save to Project] Error:", error);
    showAlert(
      `❌ Failed to save to project: ${error.message || "Unknown error"}`,
      "error",
    );
  }
}
