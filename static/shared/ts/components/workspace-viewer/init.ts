/**
 * Workspace Viewer - Auto Init
 * Initializes the shared viewer pane and wires it to the file tree.
 * Listens for file-select events from the worktree pane.
 */

import { WorkspaceViewer } from "./index.ts";

declare global {
  interface Window {
    workspaceViewer?: WorkspaceViewer;
  }
}

function getProjectId(): string {
  // Try WRITER_CONFIG (writer page)
  const writerConfig = (window as any).WRITER_CONFIG;
  if (writerConfig?.projectId) return String(writerConfig.projectId);

  // Try workspace-project-config (hub, scholar, clew) — has project_id data attr
  const configEl = document.getElementById("workspace-project-config");
  if (configEl?.dataset.projectId) return configEl.dataset.projectId;

  // Try project-data (console, project detail)
  const projectData = document.getElementById("project-data");
  if (projectData?.dataset.projectId) return projectData.dataset.projectId;

  // Try worktree tree element data attributes
  const worktreeTree = document.getElementById("ws-worktree-tree");
  if (worktreeTree?.dataset.projectId) return worktreeTree.dataset.projectId;

  return "";
}

function initWorkspaceViewer(): void {
  const tabsContainer = document.getElementById("ws-viewer-tabs");
  const monacoContainer = document.getElementById("ws-viewer-monaco");
  const mediaContainer = document.getElementById("ws-viewer-media");
  const emptyState = document.getElementById("ws-viewer-empty");

  if (!tabsContainer || !monacoContainer || !mediaContainer) return;

  const viewer = new WorkspaceViewer({
    tabsContainer,
    monacoContainer,
    mediaContainer,
    storageKey: "ws-viewer",
  });

  const projectId = getProjectId();
  if (projectId) viewer.setProjectId(projectId);

  window.workspaceViewer = viewer;

  // Hide empty state — scratch tab is always open
  if (emptyState) emptyState.style.display = "none";

  // Listen for file-select events from the worktree pane
  const worktreeTree = document.getElementById("ws-worktree-tree");
  if (worktreeTree) {
    worktreeTree.addEventListener("file-select", ((e: CustomEvent) => {
      const path = e.detail?.path;
      if (path) {
        openFileInViewer(viewer, path, emptyState);
      }
    }) as EventListener);
  }

  // Also support double-click to open (more intentional action)
  document.addEventListener("workspace-file-open", ((e: CustomEvent) => {
    const path = e.detail?.path;
    if (path) {
      openFileInViewer(viewer, path, emptyState);
    }
  }) as EventListener);
}

function openFileInViewer(
  viewer: WorkspaceViewer,
  path: string,
  emptyState: HTMLElement | null,
): void {
  // Hide empty state
  if (emptyState) emptyState.style.display = "none";

  // Auto-expand viewer pane if collapsed
  const sidebar = document.getElementById("ws-viewer-sidebar");
  if (sidebar?.classList.contains("collapsed")) {
    sidebar.classList.remove("collapsed");
    // Restore saved width or use default
    const savedWidth = localStorage.getItem("ws-viewer-width");
    sidebar.style.width = savedWidth ? `${savedWidth}px` : "480px";
  }

  void viewer.openFile(path);
}

// Auto-run on DOMContentLoaded
if (typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", () => {
    initWorkspaceViewer();
  });
}
