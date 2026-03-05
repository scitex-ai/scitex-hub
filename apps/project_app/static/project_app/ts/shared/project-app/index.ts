/**
 * Project App Orchestrator
 * Main entry point that coordinates all project_app modules
 */

// Import all modules
import * as SidebarManager from "./sidebar-manager";
import * as FileTreeManager from "./file-tree-manager";
import * as ProjectActions from "./project-actions";
import * as ProjectForms from "./project-forms";
import * as FileManager from "./file-manager";
import * as DirectoryOps from "./directory-ops";
import * as UserProfile from "./user-profile";
import * as Utils from "./utils";


// Re-export all public functions for use in other modules
export * from "./sidebar-manager";
export * from "./file-tree-manager";
export * from "./project-actions";
export * from "./project-forms";
export * from "./file-manager";
export * from "./directory-ops";
export * from "./user-profile";
export * from "./utils";

// Initialize on DOM ready
document.addEventListener("DOMContentLoaded", function () {
  console.log("project_app orchestrator: Initializing...");

  // Initialize sidebar
  SidebarManager.initializeSidebar();

  // Load file tree if on project page
  const fileTreeEl = document.getElementById("file-tree");
  if (fileTreeEl) {
    FileTreeManager.loadFileTree();
  }

  // Load project stats if on project detail page
  const watchBtn = document.getElementById("watch-btn");
  const starBtn = document.getElementById("star-btn");
  if (watchBtn || starBtn) {
    // Project stats loaded lazily when buttons are visible
  }

  console.log("project_app orchestrator: Initialization complete");
});

// Expose functions to global scope for inline onclick handlers in templates
(window as any).toggleSidebarSection = SidebarManager.toggleSidebarSection;
(window as any).toggleFolder = FileTreeManager.toggleFolder;
(window as any).handleFileUpload = FileManager.handleFileUpload;
(window as any).showNotification = Utils.showNotification;
// Init functions for form handling
(window as any).initProjectCreateForm = ProjectForms.initProjectCreateForm;
(window as any).initProjectSettingsForm = ProjectForms.initProjectSettingsForm;
(window as any).initProjectDeleteForm = ProjectForms.initProjectDeleteForm;
(window as any).showDeleteModal = ProjectForms.showDeleteModal;
(window as any).hideDeleteModal = ProjectForms.hideDeleteModal;
(window as any).submitDelete = ProjectForms.submitDelete;
// Directory operations
(window as any).toggleBranchDropdown = DirectoryOps.toggleBranchDropdown;
(window as any).toggleAddFileDropdown = DirectoryOps.toggleAddFileDropdown;
(window as any).toggleCopyDropdown = DirectoryOps.toggleCopyDropdown;
(window as any).closeAllDropdowns = DirectoryOps.closeAllDropdowns;
