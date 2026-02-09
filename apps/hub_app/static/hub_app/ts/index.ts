/**
 * Hub App - Main Entry Point
 */
import { WorkspaceFilesTree } from "@/components/workspace-files-tree/WorkspaceFilesTree";
import { initHiddenFilesToggle } from "@/components/workspace-files-tree/HiddenFilesToggle";
import { initModuleFilterButtons } from "@/components/workspace-files-tree/ModuleFilterButtons";

document.addEventListener("DOMContentLoaded", () => {
  console.log("[Hub] Initializing Hub app");

  const configEl = document.getElementById("hub-project-config");
  if (!configEl) {
    console.log("[Hub] No project config found - project selection required");
    return;
  }

  const username = configEl.dataset.username || "";
  const slug = configEl.dataset.slug || "";

  if (!username || !slug) {
    console.log("[Hub] Missing username or slug");
    return;
  }

  const treeContainer = document.getElementById("file-tree");
  if (!treeContainer) {
    console.log("[Hub] File tree container not found");
    return;
  }

  const apiUrl = `/${username}/${slug}/api/file-tree/`;

  console.log("[Hub] Initializing WorkspaceFilesTree", {
    username,
    slug,
    apiUrl,
  });

  const tree = new WorkspaceFilesTree({
    container: treeContainer,
    apiUrl,
    mode: "hub",
    username,
    projectSlug: slug,
  });

  tree.init();

  // Initialize sidebar plugins
  initHiddenFilesToggle(tree);
  initModuleFilterButtons(tree, "hub");

  console.log("[Hub] Hub ready");
});

export {};
