/**
 * SciTeX Scholar Main Index - Entry Point (Orchestrator)
 * Handles search, filters, results display, source selection, and BibTeX management
 *
 * Refactored from 768 lines to modular architecture.
 * Original: scholar-index-main_backup.ts
 */

import "./_scholar-index/utilities.ts";
import { initializeFilters } from "./_scholar-index/filters";
import {
  initializeSourceToggles,
  loadSourcePreferences,
} from "./_scholar-index/source-preferences";
import "./_scholar-index/bibtex-management.ts";
import "./_scholar-index/abstract-toggle.ts";
import "./_scholar-index/paper-actions.ts";

console.log(
  "[DEBUG] apps/scholar_app/static/scholar_app/ts/common/scholar-index-main.ts loaded",
);

// Window interface extensions
declare global {
  interface Window {
    _scholarSortInitialized?: boolean;
    scholarConfig?: {
      user?: {
        isAuthenticated?: boolean;
      };
    };
    SCHOLAR_CONFIG?: {
      urls?: {
        bibtexUpload?: string;
        resourceStatus?: string;
        search?: string;
      };
    };
  }
}

// Export to make this an ES module
export {};

// Document ready initialization
function initScholarIndexMain(): void {
  console.log("[Scholar Index Main] Initializing...");

  // Initialize all modules
  initializeFilters();
  initializeSourceToggles();

  // Load source preferences after a brief delay to ensure DOM is ready
  setTimeout(() => {
    loadSourcePreferences();
  }, 100);

  // Sort functionality
  const sortSelect = document.getElementById(
    "sortBy",
  ) as HTMLSelectElement | null;
  if (sortSelect && !window._scholarSortInitialized) {
    sortSelect.addEventListener("change", function () {
      const form = this.closest("form") as HTMLFormElement | null;
      if (form) {
        form.submit();
      }
    });
    window._scholarSortInitialized = true;
  }

  // Auto-submit when project filter changes
  const projectFilter = document.getElementById(
    "project_filter",
  ) as HTMLSelectElement | null;
  if (projectFilter) {
    projectFilter.addEventListener("change", function () {
      const form = this.closest("form") as HTMLFormElement | null;
      if (form) {
        form.submit();
      }
    });
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", function () {
    initScholarIndexMain();
  });
} else {
  initScholarIndexMain();
}
