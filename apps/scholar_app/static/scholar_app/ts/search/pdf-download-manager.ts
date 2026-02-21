/**
 * PDF Download Manager class for Scholar Search
 *
 * Handles status checks, badge updates, and download logic.
 */

import type {
  PDFStatus,
  PDFStatusResponse,
  PDFDownloadResponse,
} from "./pdf-download-types";

export class PDFDownloadManager {
  private statusCache: Map<string, PDFStatus> = new Map();
  private pendingChecks: Map<string, Promise<PDFStatusResponse>> = new Map();

  /**
   * Get CSRF token from cookie
   */
  private getCSRFToken(): string {
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
  private getCacheKey(doi?: string, arxivId?: string, pmid?: string): string {
    return `${doi || ""}:${arxivId || ""}:${pmid || ""}`;
  }

  /**
   * Check PDF status for a paper
   */
  async checkStatus(
    doi?: string,
    arxivId?: string,
    pmid?: string,
  ): Promise<PDFStatusResponse> {
    const cacheKey = this.getCacheKey(doi, arxivId, pmid);

    if (this.pendingChecks.has(cacheKey)) {
      return this.pendingChecks.get(cacheKey)!;
    }

    const params = new URLSearchParams();
    if (doi) params.set("doi", doi);
    if (arxivId) params.set("arxiv_id", arxivId);
    if (pmid) params.set("pmid", pmid);

    const promise = fetch(`/scholar/api/pdf/status/?${params.toString()}`)
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
  async downloadPDF(
    doi?: string,
    arxivId?: string,
    pmid?: string,
    pdfUrl?: string,
    title?: string,
  ): Promise<PDFDownloadResponse> {
    const response = await fetch("/scholar/api/pdf/download/", {
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
  updateBadgeStatus(
    badge: HTMLElement,
    status: PDFStatus,
    info?: { path?: string; filename?: string },
  ): void {
    badge.dataset.status = status;

    const icon = badge.querySelector("i");
    const text = badge.querySelector(".pdf-status-text");

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
  async handleBadgeClick(badge: HTMLElement): Promise<void> {
    const status = badge.dataset.status as PDFStatus;
    const doi = badge.dataset.doi || "";
    const arxivId = badge.dataset.arxivId || "";
    const pmid = badge.dataset.pmid || "";

    if (status === "downloaded" && badge.dataset.pdfPath) {
      const url = `/scholar/api/pdf/serve/?path=${encodeURIComponent(badge.dataset.pdfPath)}`;
      window.open(url, "_blank");
      return;
    }

    if (status === "available") {
      this.updateBadgeStatus(badge, "downloading");

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
   * Initialize a single badge (for dynamically added cards)
   */
  async initializeBadge(badge: HTMLElement): Promise<void> {
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

    if (!doi && !arxivId && !pmid) {
      this.updateBadgeStatus(badge, "unavailable");
      return;
    }

    badge.addEventListener("click", (e) => {
      e.stopPropagation();
      e.preventDefault();
      console.log(`[PDF] Badge clicked: status=${badge.dataset.status}`);
      this.handleBadgeClick(badge);
    });

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

    if (isOpenAccess || isFromOpenAccessSource || pdfUrl) {
      this.updateBadgeStatus(badge, "available");
      return;
    }

    this.updateBadgeStatus(badge, "unavailable");
  }

  /**
   * Download PDFs for selected papers
   */
  async downloadSelected(): Promise<{ success: number; failed: number }> {
    const selectedCards = document.querySelectorAll(
      ".result-card .paper-select:checked, .result-card-compact .paper-select-checkbox:checked",
    );

    let success = 0;
    let failed = 0;

    for (const checkbox of selectedCards) {
      const card = checkbox.closest(".result-card, .result-card-compact");
      if (!card) continue;

      const cardEl = card as HTMLElement;
      const badge = card.querySelector(".pdf-status-badge") as HTMLElement;
      const doi = cardEl.dataset.doi || badge?.dataset.doi || "";
      const arxivId = cardEl.dataset.arxivId || badge?.dataset.arxivId || "";
      const pmid = cardEl.dataset.pmid || badge?.dataset.pmid || "";
      const title = cardEl.dataset.title || "";

      if (!doi && !arxivId && !pmid) {
        failed++;
        continue;
      }

      if (badge?.dataset.status === "downloaded") {
        success++;
        continue;
      }

      try {
        if (badge) this.updateBadgeStatus(badge, "downloading");

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
          if (badge) this.updateBadgeStatus(badge, "unavailable");
          failed++;
        }
      } catch (error) {
        console.error("PDF download failed:", error);
        if (badge) this.updateBadgeStatus(badge, "error");
        failed++;
      }
    }

    return { success, failed };
  }
}
