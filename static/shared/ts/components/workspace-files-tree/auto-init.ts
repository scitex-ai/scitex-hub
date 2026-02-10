/**
 * Workspace Files Tree - Auto Init
 * Shared auto-initialization for all workspace modules.
 * Reads config from standardized #workspace-project-config element.
 * Modules can register custom handlers via window globals before DOMContentLoaded.
 */

import type { TreeItem, WorkspaceMode } from "./types.ts";
import { WorkspaceFilesTree } from "./WorkspaceFilesTree.ts";
import { initHiddenFilesToggle } from "./HiddenFilesToggle.ts";
import { initGitStatusToggle } from "./GitStatusToggle.ts";
import { initModuleFilterButtons } from "./ModuleFilterButtons.ts";

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

export async function autoInitWorkspaceTree(): Promise<WorkspaceFilesTree | null> {
  const configEl = document.getElementById("workspace-project-config");
  if (!configEl) return null;

  const username = configEl.dataset.username;
  const slug = configEl.dataset.slug;
  if (!username || !slug) return null;

  const mode = (configEl.dataset.mode || "hub") as WorkspaceMode;
  const containerId = configEl.dataset.container || "file-tree";

  const onFileSelect =
    window.scitexOnFileSelect ||
    ((path: string) => {
      window.open(`/${username}/${slug}/files/${path}`, "_blank");
    });

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
  initModuleFilterButtons(tree, mode);

  window.workspaceFilesTree = tree;

  // Notify modules that tree is ready
  if (window.scitexOnTreeDataLoaded) {
    const data = tree.getTreeData?.() ?? [];
    window.scitexOnTreeDataLoaded(data);
  }

  return tree;
}

// Auto-run on DOMContentLoaded
if (typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", () => {
    autoInitWorkspaceTree();
  });
}
