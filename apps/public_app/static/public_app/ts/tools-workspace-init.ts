/**
 * Tools workspace initialization
 * Initializes the WorkspaceFilesTree and panel toggles for tools page
 */

import { WorkspaceFilesTree } from "/static/shared/ts/components/workspace-files-tree/WorkspaceFilesTree";
import { initHiddenFilesToggle } from "/static/shared/ts/components/workspace-files-tree/HiddenFilesToggle";
import { initModuleFilterButtons } from "/static/shared/ts/components/workspace-files-tree/ModuleFilterButtons";

declare global {
  interface Window {
    toolsWorkspaceTree?: WorkspaceFilesTree;
  }
}

interface ProjectConfig {
  username: string;
  slug: string;
}

function getProjectConfig(): ProjectConfig | null {
  const configEl = document.getElementById("tools-project-config");
  if (!configEl) return null;

  const username = configEl.getAttribute("data-username");
  const slug = configEl.getAttribute("data-slug");

  if (!username || !slug) {
    console.error("[Tools] Missing project config attributes");
    return null;
  }

  return { username, slug };
}

async function initializeWorkspaceTree(config: ProjectConfig): Promise<void> {
  const tree = new WorkspaceFilesTree({
    mode: "tools",
    containerId: "file-tree",
    username: config.username,
    slug: config.slug,
    showFolderActions: true,
    showGitStatus: true,
    onFileSelect: (path: string) => {
      console.log("[Tools] File selected:", path);
      // Open file in a new tab
      window.open(`/${config.username}/${config.slug}/files/${path}`, "_blank");
    },
  });
  await tree.initialize();
  initHiddenFilesToggle(tree);
  initModuleFilterButtons(tree, "tools");
  window.toolsWorkspaceTree = tree;
}

document.addEventListener("DOMContentLoaded", async () => {
  const config = getProjectConfig();
  if (config) {
    await initializeWorkspaceTree(config);
    console.log("[Tools] Workspace initialized with project:", config.slug);
  } else {
    console.log("[Tools] No project selected - workspace disabled");
  }
});
