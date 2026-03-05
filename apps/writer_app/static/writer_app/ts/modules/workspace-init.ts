/**
 * Workspace Initialization Module
 * Handles workspace setup for new projects
 */

import { getCsrfToken } from "@/utils/csrf.js";
import { showToast } from "../utils/ui";

// Side-effect import: initializes Monaco from local bundle
import "@/_lib/monaco-init";

/**
 * Setup workspace initialization button
 */
export function setupWorkspaceInitialization(config: any): void {
  const initBtn = document.getElementById("init-writer-btn");
  if (!initBtn) {
    console.log("[Writer] Init button not found");
    return;
  }
  console.log("[Writer] Workspace init button handler attached");

  // Setup project selector
  const repoSelector = document.getElementById(
    "repository-selector",
  ) as HTMLSelectElement;
  if (repoSelector) {
    repoSelector.addEventListener("change", (e) => {
      const target = e.target as HTMLSelectElement;
      const projectId = target.value;

      if (projectId) {
        // Redirect to the selected project's writer page
        window.location.href = `/writer/project/${projectId}/`;
      }
    });
  }

  initBtn.addEventListener("click", async (e) => {
    e.preventDefault();

    // Validate project exists
    if (!config.projectId) {
      showToast(
        "Error: No project selected. Please select or create a project first.",
        "error",
      );
      initBtn.removeAttribute("disabled");
      return;
    }

    initBtn.setAttribute("disabled", "true");
    initBtn.innerHTML = "Cloning...";

    try {
      const response = await fetch("/writer/api/initialize-workspace/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrfToken(),
        },
        body: JSON.stringify({
          project_id: config.projectId,
        }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        showToast("Workspace initialized successfully", "success");
        // Small delay before reload to let user see success message
        setTimeout(() => {
          window.location.reload();
        }, 1000);
      } else {
        showToast(
          "Failed to initialize workspace: " + (data.error || "Unknown error"),
          "error",
        );
        initBtn.removeAttribute("disabled");
        initBtn.innerHTML = "Clone Template";
      }
    } catch (error) {
      showToast(
        "Error: " + (error instanceof Error ? error.message : "Unknown error"),
        "error",
      );
      initBtn.removeAttribute("disabled");
      initBtn.innerHTML = "Clone Template";
    }
  });
}

/**
 * Wait for Monaco to be available.
 * Monaco is now bundled locally (no CDN), so it's available synchronously
 * after the import above. This function is kept for API compatibility.
 */
export function waitForMonaco(_maxWaitMs?: number): Promise<boolean> {
  if ((window as any).monaco) {
    (window as any).monacoLoaded = true;
    console.log("[Writer] Monaco available (local bundle)");
    return Promise.resolve(true);
  }

  // Should never reach here with local bundling
  console.error("[Writer] Monaco not available after local import");
  return Promise.resolve(false);
}
