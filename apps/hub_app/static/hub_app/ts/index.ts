/**
 * Hub App - Main Entry Point
 */
import { WorkspaceFilesTree } from "@/components/workspace-files-tree/WorkspaceFilesTree";
import { initHiddenFilesToggle } from "@/components/workspace-files-tree/HiddenFilesToggle";
import { initModuleFilterButtons } from "@/components/workspace-files-tree/ModuleFilterButtons";

document.addEventListener("DOMContentLoaded", async () => {
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

  console.log("[Hub] Initializing WorkspaceFilesTree", { username, slug });

  const tree = new WorkspaceFilesTree({
    containerId: "file-tree",
    mode: "hub",
    username,
    slug,
  });

  await tree.initialize();

  // Initialize sidebar plugins
  initHiddenFilesToggle(tree);
  initModuleFilterButtons(tree, "hub");

  console.log("[Hub] Hub ready");
});

export {};
