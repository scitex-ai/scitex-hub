/**
 * Code Workspace TypeScript
 * Corresponds to: templates/code_app/workspace.html
 * Provides IDE-like functionality with Monaco editor and interactive terminal
 *
 * This is now a thin wrapper around the modular workspace implementation
 */

import { toggleCodeFolder } from "./file-tree-builder.js";
import { WorkspaceOrchestrator } from "./workspace/index.js";
import type { EditorConfig, Project } from "./workspace/core/types.js";

console.log("[DEBUG] apps/code_app/static/code_app/ts/workspace.ts loaded");

// Make toggleCodeFolder available globally for HTML onclick handlers
(window as any).toggleCodeFolder = toggleCodeFolder;

// Extract editor configuration from the page
function getEditorConfig(): EditorConfig {
  const projectDataEl = document.getElementById("project-data");

  if (!projectDataEl) {
    console.warn("[workspace.ts] No project data found");
    return {
      currentProject: null,
      csrfToken: getCSRFToken(),
    };
  }

  const projectId = projectDataEl.getAttribute("data-project-id");
  const projectName = projectDataEl.getAttribute("data-project-name");
  const projectOwner = projectDataEl.getAttribute("data-project-owner");
  const projectSlug = projectDataEl.getAttribute("data-project-slug");

  const currentProject: Project | null = projectId
    ? {
        id: parseInt(projectId, 10),
        name: projectName || "",
        owner: projectOwner || "",
        slug: projectSlug || "",
      }
    : null;

  return {
    currentProject,
    csrfToken: getCSRFToken(),
  };
}

function getCSRFToken(): string {
  const csrfInput = document.querySelector(
    'input[name="csrfmiddlewaretoken"]'
  ) as HTMLInputElement;
  return csrfInput?.value || "";
}

// Initialize workspace when DOM is ready
function initWorkspace() {
  console.log("[workspace.ts] Initializing Code Workspace...");

  const config = getEditorConfig();

  // Create the workspace orchestrator
  const orchestrator = new WorkspaceOrchestrator(config);

  // Expose global functions for file tree buttons
  (window as any).createFileInFolder = (folderPath: string) => {
    orchestrator.createFileInFolder(folderPath);
  };

  (window as any).createFolderInFolder = (parentPath: string) => {
    orchestrator.createFolderInFolder(parentPath);
  };

  console.log("[workspace.ts] Workspace orchestrator created");
}

// Check if DOM is already loaded (script loaded dynamically)
if (document.readyState === "loading") {
  // DOM not ready yet, wait for it
  document.addEventListener("DOMContentLoaded", initWorkspace);
} else {
  // DOM already loaded, initialize immediately
  initWorkspace();
}

// Export for debugging
(window as any).getEditorConfig = getEditorConfig;
