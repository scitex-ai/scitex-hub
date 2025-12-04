/**
 * Project App Orchestrator
 * Main entry point that coordinates all project_app modules
 */

// Import all modules
import * as SidebarManager from "./sidebar-manager.ts";
import * as FileTreeManager from "./file-tree-manager.ts";
import * as ProjectActions from "./project-actions.ts";
import * as ProjectForms from "./project-forms.ts";
import * as FileManager from "./file-manager.ts";
import * as DirectoryOps from "./directory-ops.ts";
import * as UserProfile from "./user-profile.ts";
import * as Utils from "./utils.ts";

console.log("[DEBUG] project_app orchestrator loaded");

// Re-export all public functions for use in other modules
export * from "./sidebar-manager.ts";
export * from "./file-tree-manager.ts";
export * from "./project-actions.ts";
export * from "./project-forms.ts";
export * from "./file-manager.ts";
export * from "./directory-ops.ts";
export * from "./user-profile.ts";
export * from "./utils.ts";

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
(window as any).toggleWatch = ProjectActions.toggleWatch;
(window as any).toggleStar = ProjectActions.toggleStar;
(window as any).handleForkAction = ProjectActions.handleForkAction;
(window as any).handleProjectCreate = ProjectForms.handleProjectCreate;
(window as any).handleProjectSettings = ProjectForms.handleProjectSettings;
(window as any).handleProjectDelete = ProjectForms.handleProjectDelete;
(window as any).handleFileUpload = FileManager.handleFileUpload;
(window as any).handleFileDownload = FileManager.handleFileDownload;
(window as any).copyProjectToClipboard = DirectoryOps.copyProjectToClipboard;
(window as any).searchUserRepos = UserProfile.searchUserRepos;
(window as any).showNotification = Utils.showNotification;
(window as any).confirmAction = Utils.confirmAction;
