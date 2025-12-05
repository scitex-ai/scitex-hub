/**
 * Scholar workspace initialization
 * Initializes the WorkspaceFilesTree and panel toggles for scholar mode
 */

import { WorkspaceFilesTree } from "/static/shared/ts/components/workspace-files-tree/WorkspaceFilesTree";

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
        window.open(`/${config.username}/${config.slug}/files/${path}`, "_blank");
      } else if (path.endsWith(".bib")) {
        console.log("BibTeX file selected:", path);
      }
    },
  });
  await tree.initialize();
  window.scholarWorkspaceTree = tree;
}

function initializePanelToggles(): void {
  // Sidebar toggle
  const toggleBtn = document.getElementById("sidebar-toggle");
  const sidebar = document.getElementById("scholar-sidebar");
  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener("click", () => {
      sidebar.classList.toggle("collapsed");
      const icon = toggleBtn.querySelector("i");
      if (icon) {
        icon.classList.toggle("fa-chevron-left");
        icon.classList.toggle("fa-chevron-right");
      }
    });
  }

  // Properties panel toggle
  const propsToggleBtn = document.getElementById("properties-toggle");
  const propsPanel = document.getElementById("scholar-properties");
  if (propsToggleBtn && propsPanel) {
    propsToggleBtn.addEventListener("click", () => {
      propsPanel.classList.toggle("collapsed");
      const icon = propsToggleBtn.querySelector("i");
      if (icon) {
        icon.classList.toggle("fa-chevron-right");
        icon.classList.toggle("fa-chevron-left");
      }
    });
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  const config = getProjectConfig();
  if (config) {
    await initializeWorkspaceTree(config);
  }
  initializePanelToggles();
  console.log("[Scholar] Workspace initialized");
});
