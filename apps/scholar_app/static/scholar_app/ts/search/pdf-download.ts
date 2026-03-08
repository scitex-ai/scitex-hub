/**
 * PDF Download Handler for Scholar Search
 *
 * Provides PDF download functionality with status badges and
 * integration with the search results UI.
 */
/**
 * PDF Download Manager
 */
class PDFDownloadManager {
  constructor() {
    this.statusCache = new Map();
    this.pendingChecks = new Map();
  }
  /**
   * Get CSRF token from cookie
   */
  getCSRFToken() {
    const name = "csrftoken";
    const cookies = document.cookie.split(";");
    for (const cookie of cookies) {
      const trimmed = cookie.trim();
      if (trimmed.startsWith(name + "=")) {
        return decodeURIComponent(trimmed.substring(name.length + 1));
      }
    }
    return "";
  }
  /**
   * Generate cache key from identifiers
   */
  getCacheKey(doi, arxivId, pmid) {
    return `${doi || ""}:${arxivId || ""}:${pmid || ""}`;
  }
  /**
   * Check PDF status for a paper
   */
  async checkStatus(doi, arxivId, pmid) {
    const cacheKey = this.getCacheKey(doi, arxivId, pmid);
    // Return cached result if available
    if (this.pendingChecks.has(cacheKey)) {
      return this.pendingChecks.get(cacheKey);
    }
    const params = new URLSearchParams();
    if (doi) params.set("doi", doi);
    if (arxivId) params.set("arxiv_id", arxivId);
    if (pmid) params.set("pmid", pmid);
    const promise = fetch(`/apps/scholar/api/pdf/status/?${params.toString()}`)
      .then((response) => response.json())
      .finally(() => {
        this.pendingChecks.delete(cacheKey);
      });
    this.pendingChecks.set(cacheKey, promise);
    return promise;
  }
  /**
   * Download PDF for a paper
   */
  async downloadPDF(doi, arxivId, pmid, pdfUrl, title) {
    const response = await fetch("/apps/scholar/api/pdf/download/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": this.getCSRFToken(),
      },
      body: JSON.stringify({
        doi,
        arxiv_id: arxivId,
        pmid,
        pdf_url: pdfUrl,
        title: title || "paper",
        prefer_open_access: true,
      }),
    });
    return response.json();
  }
  /**
   * Update badge status for a paper
   */
  updateBadgeStatus(badge, status, info) {
    badge.dataset.status = status;
    const icon = badge.querySelector("i");
    const text = badge.querySelector(".pdf-status-text");
    // Update icon and text based on status
    switch (status) {
      case "checking":
        if (icon) icon.className = "fas fa-spinner fa-spin";
        if (text) text.textContent = "...";
        badge.title = "Checking PDF availability...";
        break;
      case "available":
        if (icon) icon.className = "fas fa-file-pdf";
        if (text) text.textContent = "Get PDF";
        badge.title = "Click to download PDF";
        badge.classList.add("clickable");
        break;
      case "downloading":
        if (icon) icon.className = "fas fa-spinner fa-spin";
        if (text) text.textContent = "Downloading...";
        badge.title = "Downloading PDF...";
        break;
      case "downloaded":
        if (icon) icon.className = "fas fa-file-pdf";
        if (text) text.textContent = "View PDF";
        badge.title = info?.filename || "PDF available - click to view";
        badge.classList.add("clickable", "downloaded");
        if (info?.path) {
          badge.dataset.pdfPath = info.path;
        }
        break;
      case "unavailable":
        if (icon) icon.className = "fas fa-lock";
        if (text) text.textContent = "Paywalled";
        badge.title = "PDF requires subscription (not open access)";
        badge.classList.add("unavailable");
        break;
      case "error":
        if (icon) icon.className = "fas fa-exclamation-triangle";
        if (text) text.textContent = "Error";
        badge.title = "Failed to check PDF status";
        badge.classList.add("error");
        break;
      default:
        if (icon) icon.className = "fas fa-file-pdf";
        if (text) text.textContent = "PDF";
        badge.title = "PDF status unknown";
    }
  }
  /**
   * Handle badge click
   */
  async handleBadgeClick(badge) {
    const status = badge.dataset.status;
    const doi = badge.dataset.doi || "";
    const arxivId = badge.dataset.arxivId || "";
    const pmid = badge.dataset.pmid || "";
    if (status === "downloaded" && badge.dataset.pdfPath) {
      // Open PDF in new tab
      const url = `/apps/scholar/api/pdf/serve/?path=${encodeURIComponent(badge.dataset.pdfPath)}`;
      window.open(url, "_blank");
      return;
    }
    if (status === "available") {
      // Start download
      this.updateBadgeStatus(badge, "downloading");
      // Get title from parent card
      const card = badge.closest(".result-card, .result-card-compact");
      const titleEl = card?.querySelector(
        ".result-title a, .result-title-link",
      );
      const title = titleEl?.textContent?.trim() || "paper";
      try {
        const result = await this.downloadPDF(
          doi,
          arxivId,
          pmid,
          undefined,
          title,
        );
        if (result.downloaded && result.path) {
          this.updateBadgeStatus(badge, "downloaded", {
            path: result.path,
            filename: result.filename,
          });
        } else {
          this.updateBadgeStatus(badge, "unavailable");
        }
      } catch (error) {
        console.error("PDF download failed:", error);
        this.updateBadgeStatus(badge, "error");
      }
    }
  }
  /**
   * Initialize badges for all result cards on page
   */
  async initializeBadges() {
    const badges = document.querySelectorAll(
      ".pdf-status-badge[data-status='unknown']",
    );
    for (const badge of badges) {
      const badgeEl = badge;
      const doi = badgeEl.dataset.doi || "";
      const arxivId = badgeEl.dataset.arxivId || "";
      const pmid = badgeEl.dataset.pmid || "";
      if (!doi && !arxivId && !pmid) {
        this.updateBadgeStatus(badgeEl, "unavailable");
        continue;
      }
      // Add click handler
      badgeEl.addEventListener("click", (e) => {
        e.stopPropagation();
        this.handleBadgeClick(badgeEl);
      });
      // Check status
      this.updateBadgeStatus(badgeEl, "checking");
      try {
        const result = await this.checkStatus(doi, arxivId, pmid);
        if (result.has_pdf) {
          this.updateBadgeStatus(badgeEl, "downloaded", {
            path: result.path,
            filename: result.filename,
          });
        } else if (result.can_download) {
          this.updateBadgeStatus(badgeEl, "available");
        } else {
          this.updateBadgeStatus(badgeEl, "unavailable");
        }
      } catch (error) {
        console.error("Failed to check PDF status:", error);
        this.updateBadgeStatus(badgeEl, "error");
      }
    }
  }
  /**
   * Initialize a single badge (for dynamically added cards)
   */
  async initializeBadge(badge) {
    // Skip if already initialized (has click handler)
    if (badge.dataset.initialized === "true") {
      return;
    }
    badge.dataset.initialized = "true";
    const doi = badge.dataset.doi || "";
    const arxivId = badge.dataset.arxivId || "";
    const pmid = badge.dataset.pmid || "";
    const isOpenAccess = badge.dataset.isOpenAccess === "true";
    const source = badge.dataset.source || "";
    const pdfUrl = badge.dataset.pdfUrl || "";
    // Debug logging disabled for performance (uncomment if needed)
    // console.log(`[PDF] Initializing badge: doi=${doi}, arxiv=${arxivId}, isOA=${isOpenAccess}, source=${source}`);
    if (!doi && !arxivId && !pmid) {
      this.updateBadgeStatus(badge, "unavailable");
      return;
    }
    // Add click handler
    badge.addEventListener("click", (e) => {
      e.stopPropagation();
      e.preventDefault();
      console.log(`[PDF] Badge clicked: status=${badge.dataset.status}`);
      this.handleBadgeClick(badge);
    });
    // Check if this is from an open access source
    const openAccessSources = [
      "arxiv",
      "pmc",
      "biorxiv",
      "medrxiv",
      "doaj",
      "plos",
    ];
    const isFromOpenAccessSource =
      openAccessSources.includes(source.toLowerCase()) || !!arxivId;
    // If we already know it's open access (from search result), mark as available
    if (isOpenAccess || isFromOpenAccessSource || pdfUrl) {
      this.updateBadgeStatus(badge, "available");
      return;
    }
    // For others (likely paywalled), mark as unavailable without checking
    // This avoids unnecessary API calls for papers we can't download anyway
    this.updateBadgeStatus(badge, "unavailable");
  }
  /**
   * Download PDFs for selected papers
   */
  async downloadSelected() {
    const selectedCards = document.querySelectorAll(
      ".result-card .paper-select:checked, .result-card-compact .paper-select-checkbox:checked",
    );
    let success = 0;
    let failed = 0;
    for (const checkbox of selectedCards) {
      const card = checkbox.closest(".result-card, .result-card-compact");
      if (!card) continue;
      const cardEl = card;
      const badge = card.querySelector(".pdf-status-badge");
      const doi = cardEl.dataset.doi || badge?.dataset.doi || "";
      const arxivId = cardEl.dataset.arxivId || badge?.dataset.arxivId || "";
      const pmid = cardEl.dataset.pmid || badge?.dataset.pmid || "";
      const title = cardEl.dataset.title || "";
      if (!doi && !arxivId && !pmid) {
        failed++;
        continue;
      }
      // Skip if already downloaded
      if (badge?.dataset.status === "downloaded") {
        success++;
        continue;
      }
      try {
        if (badge) {
          this.updateBadgeStatus(badge, "downloading");
        }
        const result = await this.downloadPDF(
          doi,
          arxivId,
          pmid,
          undefined,
          title,
        );
        if (result.downloaded && badge) {
          this.updateBadgeStatus(badge, "downloaded", {
            path: result.path,
            filename: result.filename,
          });
          success++;
        } else {
          if (badge) {
            this.updateBadgeStatus(badge, "unavailable");
          }
          failed++;
        }
      } catch (error) {
        console.error("PDF download failed:", error);
        if (badge) {
          this.updateBadgeStatus(badge, "error");
        }
        failed++;
      }
    }
    return { success, failed };
  }
}
// Create singleton instance
const pdfManager = new PDFDownloadManager();
window.pdfDownloadManager = pdfManager;
// Deferred badge initialization - don't block rendering
let pendingBadges = [];
let initializationScheduled = false;
function scheduleInitialization() {
  if (initializationScheduled) return;
  initializationScheduled = true;
  // Use requestIdleCallback if available, otherwise requestAnimationFrame
  const scheduleCallback =
    window.requestIdleCallback || window.requestAnimationFrame;
  scheduleCallback(() => {
    initializationScheduled = false;
    const badges = pendingBadges.splice(0); // Take all pending badges
    if (badges.length > 0) {
      // Initialize in small batches to avoid blocking
      const BATCH_SIZE = 10;
      let index = 0;
      function initBatch() {
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
// Initialize on DOM ready
document.addEventListener("DOMContentLoaded", () => {
  console.log("[PDF Download] Initializing PDF download manager...");
  // Initialize existing badges (deferred)
  const existingBadges = document.querySelectorAll(
    ".pdf-status-badge[data-status='unknown']",
  );
  existingBadges.forEach((badge) => pendingBadges.push(badge));
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
            // Find any uninitialized PDF badge - queue for deferred initialization
            const badges = node.querySelectorAll(
              ".pdf-status-badge:not([data-initialized='true'])",
            );
            badges.forEach((badge) => pendingBadges.push(badge));
            // Also check if the node itself is a badge
            if (
              node.classList.contains("pdf-status-badge") &&
              node.dataset.initialized !== "true"
            ) {
              pendingBadges.push(node);
            }
          }
        }
      }
      // Schedule batch initialization after mutations settle
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
      const btn = document.getElementById("actionDownloadPdfs");
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
});
export {};
//# sourceMappingURL=pdf-download.ts.map
