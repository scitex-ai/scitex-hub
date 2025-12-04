/**
 * Workspace Initialization Module
 * Handles workspace setup for new projects
 */

import { getCsrfToken } from "@/utils/csrf.js";
import { showToast } from "../utils/ui.js";

/**
 * Setup workspace initialization button
 */
export function setupWorkspaceInitialization(config: any): void {
  const initBtn = document.getElementById("init-writer-btn");
  if (!initBtn) return;

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
    initBtn.innerHTML =
      '<i class="fas fa-spinner fa-spin me-2"></i>Creating workspace...';

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
        initBtn.innerHTML =
          '<i class="fas fa-rocket me-2"></i>Create Workspace';
      }
    } catch (error) {
      showToast(
        "Error: " + (error instanceof Error ? error.message : "Unknown error"),
        "error",
      );
      initBtn.removeAttribute("disabled");
      initBtn.innerHTML = '<i class="fas fa-rocket me-2"></i>Create Workspace';
    }
  });
}

/**
 * Wait for Monaco to load asynchronously
 */
export async function waitForMonaco(
  maxWaitMs: number = 10000,
): Promise<boolean> {
  const startTime = Date.now();
  console.log("[Writer] Waiting for Monaco to load...");

  while (Date.now() - startTime < maxWaitMs) {
    if ((window as any).monacoLoaded && (window as any).monaco) {
      console.log("[Writer] Monaco loaded successfully");
      return true;
    }
    // Wait 100ms before checking again
    await new Promise((resolve) => setTimeout(resolve, 100));
  }

  console.warn(
    "[Writer] Monaco failed to load within timeout, will fallback to CodeMirror",
  );
  return false;
}
