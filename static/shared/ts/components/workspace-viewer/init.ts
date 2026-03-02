/**
 * Workspace Viewer - Auto Init
 * Initializes the shared viewer pane and wires it to the file tree.
 * Listens for file-select events from the worktree pane.
 */

import { WorkspaceViewer } from "./index";

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

  const previewContainer =
    document.getElementById("ws-viewer-preview") ?? undefined;
  const modeToggle =
    document.getElementById("ws-viewer-mode-toggle") ?? undefined;

  const viewer = new WorkspaceViewer({
    tabsContainer,
    monacoContainer,
    mediaContainer,
    previewContainer,
    modeToggle,
    storageKey: "ws-viewer",
  });

  const projectId = getProjectId();
  if (projectId) viewer.setProjectId(projectId);

  window.workspaceViewer = viewer;

  // Show empty state until a file is opened
  if (emptyState) emptyState.style.display = "";

  // Listen for file-select events from ANY tree container (worktree pane or module tree).
  // The event has bubbles: true, so listening on document catches them all.
  document.addEventListener("file-select", ((e: CustomEvent) => {
    const path = e.detail?.path;
    if (path) {
      openFileInViewer(viewer, path, emptyState);
    }
  }) as EventListener);

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

  // Track file open in navigation history (debounced for rapid clicks)
  window._appNav?.push({ file: path });
}

// Restore file on back/forward navigation
function registerNavRestore(): void {
  window._appNav?.onRestore((state) => {
    if (state.file && window.workspaceViewer) {
      const emptyState = document.getElementById("ws-viewer-empty");
      openFileInViewer(window.workspaceViewer, state.file, emptyState);
    }
  });
}

// Auto-run on DOMContentLoaded
if (typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", () => {
    initWorkspaceViewer();
    registerNavRestore();
  });
}
