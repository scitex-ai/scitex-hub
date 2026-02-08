/**
 * Scholar workspace initialization
 * Initializes the WorkspaceFilesTree and panel toggles for scholar mode
 */

import { WorkspaceFilesTree } from "/static/shared/ts/components/workspace-files-tree/WorkspaceFilesTree";
import { initHiddenFilesToggle } from "/static/shared/ts/components/workspace-files-tree/HiddenFilesToggle";
import { initModuleFilterToggle } from "/static/shared/ts/components/workspace-files-tree/ModuleFilterToggle";

// Import PDF download handler (auto-initializes on DOM ready)
import "./search/pdf-download";

// Import search main functionality (auto-initializes on DOM ready)
import "./search/search-main";

declare global {
  interface Window {
    scholarWorkspaceTree?: WorkspaceFilesTree;
  }
}

interface ProjectConfig {
  username: string;
  slug: string;
}

function getProjectConfig(): ProjectConfig | null {
  const configEl = document.getElementById("scholar-project-config");
  if (!configEl) return null;

  try {
    return JSON.parse(configEl.textContent || "{}");
  } catch {
    console.error("[Scholar] Failed to parse project config");
    return null;
  }
}

async function initializeWorkspaceTree(config: ProjectConfig): Promise<void> {
  const tree = new WorkspaceFilesTree({
    mode: "scholar",
    containerId: "file-tree",
    username: config.username,
    slug: config.slug,
    showFolderActions: true,
    showGitStatus: true,
    onFileSelect: (path: string) => {
      console.log("[Scholar] File selected:", path);
      if (path.endsWith(".pdf")) {
        window.open(
          `/${config.username}/${config.slug}/files/${path}`,
          "_blank",
        );
      } else if (path.endsWith(".bib")) {
        console.log("BibTeX file selected:", path);
      }
    },
  });
  await tree.initialize();
  initHiddenFilesToggle(tree);
  initModuleFilterToggle(tree);
  window.scholarWorkspaceTree = tree;
}

// Panel toggles are handled by inline JS in scholar_unified.html
// which includes localStorage persistence for state

document.addEventListener("DOMContentLoaded", async () => {
  const config = getProjectConfig();
  if (config) {
    await initializeWorkspaceTree(config);
  }
  console.log("[Scholar] Workspace initialized");
});
