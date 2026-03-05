/**
 * Workspace Files Tree - Auto Init
 * Shared auto-initialization for all workspace modules.
 * Reads config from standardized #workspace-project-config element.
 * Modules can register custom handlers via window globals before DOMContentLoaded.
 */

import type { TreeItem, WorkspaceMode } from "./types";
import { WorkspaceFilesTree } from "./WorkspaceFilesTree";
import { initHiddenFilesToggle } from "./_HiddenFilesToggle";
import { initGitStatusToggle } from "./_GitStatusToggle";
import { initModuleFilterButtons } from "./_ModuleFilterButtons";
import { initSortToggle } from "./_SortToggle";
import {
  initMonitorToggle,
  initRepoMonitor,
  RepoMonitorClient,
} from "../repo-monitor/index";

declare global {
  interface Window {
    /** Custom file select handler (set by module before DOMContentLoaded) */
    scitexOnFileSelect?: (path: string, item: TreeItem) => void;
    /** Custom tree data loaded handler (set by module before DOMContentLoaded) */
    scitexOnTreeDataLoaded?: (data: TreeItem[]) => void;
    /** Shared tree instance (set by auto-init after initialization) */
    workspaceFilesTree?: WorkspaceFilesTree;
  }
}

/**
 * Wire repo monitor fs_events to tree.refresh() with debounce.
 * This replaces polling — the tree updates only when files actually change.
 */
function wireRepoMonitorToTree(
  client: RepoMonitorClient,
  tree: WorkspaceFilesTree,
): void {
  let debounceTimer: ReturnType<typeof setTimeout> | null = null;
  const DEBOUNCE_MS = 500;

  client.onEvent(() => {
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      tree.refresh().catch(console.error);
    }, DEBOUNCE_MS);
  });
}

/**
 * Try to initialize repo monitor and wire it to the tree.
 * Returns the client if successful, null otherwise.
 */
function initRepoMonitorForTree(
  tree: WorkspaceFilesTree,
  username: string,
  slug: string,
): RepoMonitorClient | null {
  const monitorEl = document.getElementById("ws-repo-monitor");
  const projectId = monitorEl?.dataset.projectId;
  if (!projectId) return null;

  const client = initRepoMonitor({ projectId, username, slug });
  if (client) {
    wireRepoMonitorToTree(client, tree);
  }
  return client;
}

export async function autoInitWorkspaceTree(): Promise<WorkspaceFilesTree | null> {
  const configEl = document.getElementById("workspace-project-config");
  if (!configEl) return null;

  const username = configEl.dataset.username;
  const slug = configEl.dataset.slug;
  if (!username || !slug) return null;

  const mode = (configEl.dataset.mode || "hub") as WorkspaceMode;
  const containerId = configEl.dataset.container || "file-tree";

  // Skip if container element doesn't exist (e.g. three-column layout uses worktree pane instead)
  if (!document.getElementById(containerId)) return null;

  // Single click delegates to custom handler; default does nothing (dblclick navigates)
  const onFileSelect = window.scitexOnFileSelect || (() => {});

  const tree = new WorkspaceFilesTree({
    mode,
    containerId,
    username,
    slug,
    showFolderActions: true,
    showGitStatus: true,
    onFileSelect,
  });

  await tree.initialize();
  initHiddenFilesToggle(tree);
  initGitStatusToggle(tree);
  initSortToggle(tree);
  initModuleFilterButtons(tree, mode);

  window.workspaceFilesTree = tree;

  // Notify modules that tree is ready
  if (window.scitexOnTreeDataLoaded) {
    const data = tree.getTreeData?.() ?? [];
    window.scitexOnTreeDataLoaded(data);
  }

  // Wire repo monitor → tree refresh (replaces polling)
  initRepoMonitorForTree(tree, username, slug);

  return tree;
}

/**
 * Initialize WorkspaceFilesTree for [data-workspace-tree] elements.
 * Used by the three-column layout's shared worktree pane.
 * This path is separate from #workspace-project-config (used by hub/scholar/clew).
 */
export async function autoInitWorktreePanes(): Promise<void> {
  const panes = document.querySelectorAll<HTMLElement>("[data-workspace-tree]");
  if (panes.length === 0) return;

  for (const pane of panes) {
    // Ensure the element has an ID for WorkspaceFilesTree containerId
    if (!pane.id) {
      pane.id = "ws-worktree-tree";
    }

    const slug = pane.dataset.projectSlug;
    const username = pane.dataset.username;
    if (!slug || !username) continue;

    // Delegate to custom handler if set; file viewing handled by workspace-viewer pane
    const onFileSelect = window.scitexOnFileSelect || (() => {});

    const tree = new WorkspaceFilesTree({
      mode: "hub" as WorkspaceMode,
      containerId: pane.id,
      username,
      slug,
      showFolderActions: true,
      showGitStatus: true,
      onFileSelect,
    });

    await tree.initialize();

    initHiddenFilesToggle(tree);
    initGitStatusToggle(tree);
    initSortToggle(tree);
    initModuleFilterButtons(tree, "hub");

    window.workspaceFilesTree = tree;

    // Notify modules that tree is ready
    if (window.scitexOnTreeDataLoaded) {
      const data = tree.getTreeData?.() ?? [];
      window.scitexOnTreeDataLoaded(data);
    }

    // Initialize repository monitor toggle (always — collapse/expand + localStorage)
    initMonitorToggle();

    // Wire repo monitor → tree refresh (replaces polling)
    let currentMonitorClient = initRepoMonitorForTree(tree, username, slug);

    // Listen for project switch — reinitialize tree + repo monitor
    window.addEventListener("scitex:project-switched", (async (
      e: CustomEvent<{ slug: string; id: string; owner?: string }>,
    ) => {
      const newSlug = e.detail.slug;
      const newOwner = e.detail.owner || username;
      if (!newSlug) return;

      // Update DOM data attributes
      pane.dataset.projectSlug = newSlug;
      pane.dataset.username = newOwner;

      // Update sidebar title
      const titleFull = document.querySelector(
        ".sidebar-title-full",
      ) as HTMLElement;
      if (titleFull) {
        titleFull.innerHTML = `<i class="fas fa-folder-open"></i> ${newOwner}/${newSlug}`;
      }

      // Update project ID on config elements (used by viewer's getProjectId())
      const configEl = document.getElementById("workspace-project-config");
      if (configEl) {
        configEl.dataset.projectId = e.detail.id;
        configEl.dataset.slug = newSlug;
        configEl.dataset.username = newOwner;
      }

      // Update repo monitor project ID
      const monitorEl = document.getElementById("ws-repo-monitor");
      if (monitorEl) {
        monitorEl.dataset.projectId = e.detail.id;
      }

      // Destroy old tree and create new one
      pane.innerHTML = "";
      const newTree = new WorkspaceFilesTree({
        mode: "hub" as WorkspaceMode,
        containerId: pane.id,
        username: newOwner,
        slug: newSlug,
        showFolderActions: true,
        showGitStatus: true,
        onFileSelect: window.scitexOnFileSelect || (() => {}),
      });

      await newTree.initialize();
      initHiddenFilesToggle(newTree);
      initGitStatusToggle(newTree);
      initSortToggle(newTree);
      initModuleFilterButtons(newTree, "hub");
      window.workspaceFilesTree = newTree;

      // Disconnect old monitor, wire new one
      if (currentMonitorClient) {
        currentMonitorClient.disconnect();
      }
      currentMonitorClient = initRepoMonitorForTree(newTree, newOwner, newSlug);
    }) as EventListener);
  }
}

// Auto-run on DOMContentLoaded
if (typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", () => {
    // Monitor toggle works even without a tree — always init
    initMonitorToggle();
    // Primary init: module-owned trees via #workspace-project-config (hub, scholar, clew)
    autoInitWorkspaceTree();
    // Secondary init: shared worktree pane in three-column layout via [data-workspace-tree]
    autoInitWorktreePanes();
  });
}
