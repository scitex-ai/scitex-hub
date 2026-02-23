/**
 * Project Detail Page - Main Entry Point (Orchestrator)
 * Handles project detail page functionality
 *
 * Refactored from 774 lines to modular architecture.
 * Original: detail_backup.ts
 */

import {
  loadFileTree as loadFileTreeShared,
  toggleFolder as toggleFolderShared,
} from "../shared/file-tree";
import {
  initializeSidebar,
  toggleSidebar,
  toggleSidebarSection,
} from "./detail/sidebar";
import {
  copyProjectToClipboard,
  downloadProjectAsFile,
} from "./detail/project-concatenation";
import {
  loadProjectStats,
  toggleWatch,
  toggleStar,
  forkProject,
} from "./detail/project-actions";
import {
  toggleBranchDropdown,
  switchBranch,
  toggleAddFileDropdown,
  toggleCodeDropdown,
  toggleCopyDropdown,
  toggleImportExportDropdown,
  showImportModal,
  handleExport,
  closeAllDropdowns,
} from "./detail/toolbar-dropdowns";
import { copyCloneUrl, downloadProjectZip } from "./detail/clone-download";

console.log(
  "[DEBUG] apps/project_app/static/project_app/ts/projects/detail.ts loaded",
);

(function () {
  "use strict";

  // Use shared toggle function
  function toggleFolder(folderId: string, event?: Event): void {
    toggleFolderShared(folderId, event);
  }

  function loadFileTree(): void {
    loadFileTreeShared();
  }

  // Initialize on DOM ready
  document.addEventListener("DOMContentLoaded", function () {
    console.log("Page loaded - initializing sidebar, file tree and dropdown");

    initializeSidebar();
    loadFileTree();
    loadProjectStats();

    // Make table rows clickable
    const fileBrowserRows = document.querySelectorAll(".file-browser-row");
    fileBrowserRows.forEach((row: Element) => {
      row.addEventListener("click", function (this: HTMLElement, e: Event) {
        const target = e.target as HTMLElement;
        if (target.tagName === "A" || target.closest("a")) {
          return;
        }
        const href = this.getAttribute("data-href");
        if (href) {
          window.location.href = href;
        }
      });
    });

    // Manual dropdown toggle for split button
    const dropdownToggle = document.querySelector(".dropdown-toggle-split");
    const dropdownMenu = document.querySelector(
      ".dropdown-menu",
    ) as HTMLElement | null;

    if (dropdownToggle && dropdownMenu) {
      console.log("Dropdown elements found - setting up manual toggle");

      dropdownToggle.addEventListener("click", function (e) {
        console.log("Dropdown toggle clicked!");
        e.preventDefault();
        e.stopPropagation();

        const isVisible = dropdownMenu.style.display === "block";
        dropdownMenu.style.display = isVisible ? "none" : "block";
        console.log(
          "Dropdown visibility toggled to:",
          dropdownMenu.style.display,
        );
      });

      // Close dropdown when clicking outside
      document.addEventListener("click", function (e) {
        const target = e.target as Node;
        if (
          !dropdownToggle.contains(target) &&
          !dropdownMenu.contains(target)
        ) {
          dropdownMenu.style.display = "none";
        }
      });
    } else {
      console.warn("Dropdown elements not found:", {
        dropdownToggle,
        dropdownMenu,
      });
    }
  });

  // Close dropdowns when clicking outside
  document.addEventListener("click", function (e: Event) {
    const target = e.target as HTMLElement;
    const clickedButton = target.closest("button");
    const isDropdownButton =
      clickedButton &&
      (clickedButton.id === "branch-dropdown-btn-header" ||
        clickedButton.id === "add-file-btn" ||
        clickedButton.classList.contains("dropdown-toggle-split"));
    const isDropdownContent = target.closest(".dropdown-menu");

    if (!isDropdownButton && !isDropdownContent) {
      closeAllDropdowns();
    }
  });

  // Expose functions to global scope for onclick handlers
  (window as any).toggleSidebar = toggleSidebar;
  (window as any).toggleSidebarSection = toggleSidebarSection;
  (window as any).toggleFolder = toggleFolder;
  (window as any).copyProjectToClipboard = copyProjectToClipboard;
  (window as any).downloadProjectAsFile = downloadProjectAsFile;
  (window as any).toggleBranchDropdown = toggleBranchDropdown;
  (window as any).switchBranch = switchBranch;
  (window as any).toggleWatch = toggleWatch;
  (window as any).toggleStar = toggleStar;
  (window as any).forkProject = forkProject;
  (window as any).toggleAddFileDropdown = toggleAddFileDropdown;
  (window as any).toggleCodeDropdown = toggleCodeDropdown;
  (window as any).toggleCopyDropdown = toggleCopyDropdown;
  (window as any).toggleImportExportDropdown = toggleImportExportDropdown;
  (window as any).showImportModal = showImportModal;
  (window as any).handleExport = handleExport;
  (window as any).copyCloneUrl = copyCloneUrl;
  (window as any).downloadProjectZip = downloadProjectZip;
})();
