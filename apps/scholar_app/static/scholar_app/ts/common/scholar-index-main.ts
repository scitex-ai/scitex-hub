/**
 * SciTeX Scholar Main Index - Entry Point (Orchestrator)
 * Handles search, filters, results display, source selection, and BibTeX management
 *
 * Refactored from 768 lines to modular architecture.
 * Original: scholar-index-main_backup.ts
 */

import './scholar-index/utilities.ts';
import { initializeFilters } from './scholar-index/filters.ts';
import {
  initializeSourceToggles,
  loadSourcePreferences
} from './scholar-index/source-preferences.ts';
import './scholar-index/bibtex-management.js';
import './scholar-index/abstract-toggle.js';
import './scholar-index/paper-actions.js';

console.log("[DEBUG] apps/scholar_app/static/scholar_app/ts/common/scholar-index-main.ts loaded");

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
document.addEventListener("DOMContentLoaded", function () {
  console.log("[Scholar Index Main] Initializing...");

  // Initialize all modules
  initializeFilters();
  initializeSourceToggles();

  // Load source preferences after a brief delay to ensure DOM is ready
  setTimeout(() => {
    loadSourcePreferences();
  }, 100);

  // Sort functionality
  const sortSelect = document.getElementById("sortBy") as HTMLSelectElement | null;
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
  const projectFilter = document.getElementById("project_filter") as HTMLSelectElement | null;
  if (projectFilter) {
    projectFilter.addEventListener("change", function () {
      const form = this.closest("form") as HTMLFormElement | null;
      if (form) {
        form.submit();
      }
    });
  }
});
