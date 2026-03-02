/**
 * PDF Download Handler for Scholar Search (orchestrator)
 *
 * Initializes the PDF download manager and sets up DOM observers.
 * Core logic lives in pdf-download-manager.ts.
 */

console.log(
  "[DEBUG] apps/scholar_app/static/scholar_app/ts/search/pdf-download.ts loaded",
);

import { PDFDownloadManager } from "./_pdf-download-manager";

// Create singleton instance
const pdfManager = new PDFDownloadManager();

// Expose to window for use by other scripts
declare global {
  interface Window {
    pdfDownloadManager: PDFDownloadManager;
  }
}
window.pdfDownloadManager = pdfManager;

// Deferred badge initialization - don't block rendering
let pendingBadges: HTMLElement[] = [];
let initializationScheduled = false;

function scheduleInitialization(): void {
  if (initializationScheduled) return;
  initializationScheduled = true;

  const scheduleCallback =
    (window as any).requestIdleCallback || window.requestAnimationFrame;
  scheduleCallback(() => {
    initializationScheduled = false;
    const badges = pendingBadges.splice(0);
    if (badges.length > 0) {
      const BATCH_SIZE = 10;
      let index = 0;

      function initBatch(): void {
        const batch = badges.slice(index, index + BATCH_SIZE);
        batch.forEach((badge) => pdfManager.initializeBadge(badge));
        index += BATCH_SIZE;
        if (index < badges.length) {
          requestAnimationFrame(initBatch);
        }
      }
      initBatch();
    }
  });
}

function initPdfDownload(): void {
  console.log("[PDF Download] Initializing PDF download manager...");

  // Initialize existing badges (deferred)
  const existingBadges = document.querySelectorAll(
    ".pdf-status-badge[data-status='unknown']",
  );
  existingBadges.forEach((badge) => pendingBadges.push(badge as HTMLElement));
  if (pendingBadges.length > 0) {
    scheduleInitialization();
  }

  // Setup mutation observer for dynamically added cards
  const resultsContainer = document.getElementById("progressiveResults");
  if (resultsContainer) {
    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        for (const node of mutation.addedNodes) {
          if (node instanceof HTMLElement) {
            const badges = node.querySelectorAll(
              ".pdf-status-badge:not([data-initialized='true'])",
            );
            badges.forEach((badge) => pendingBadges.push(badge as HTMLElement));
            if (
              node.classList.contains("pdf-status-badge") &&
              node.dataset.initialized !== "true"
            ) {
              pendingBadges.push(node);
            }
          }
        }
      }
      if (pendingBadges.length > 0) {
        scheduleInitialization();
      }
    });

    observer.observe(resultsContainer, { childList: true, subtree: true });
    console.log(
      "[PDF Download] MutationObserver setup with deferred initialization",
    );
  }

  // Setup download selected handler
  document
    .getElementById("actionDownloadPdfs")
    ?.addEventListener("click", async () => {
      const btn = document.getElementById(
        "actionDownloadPdfs",
      ) as HTMLButtonElement;
      if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Downloading...';
      }

      const result = await pdfManager.downloadSelected();

      if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-file-pdf"></i> PDFs';
      }

      alert(`Downloaded: ${result.success}, Failed: ${result.failed}`);
    });

  console.log("[PDF Download] Initialization complete");
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", function () {
    initPdfDownload();
  });
} else {
  initPdfDownload();
}
