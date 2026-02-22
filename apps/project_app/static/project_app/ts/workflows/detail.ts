// Workflow Detail Page JavaScript
// Functions for triggering and toggling workflows

console.log(
  "[DEBUG] apps/project_app/static/project_app/ts/workflows/detail.ts loaded",
);

(function () {
  "use strict";

  interface WorkflowResponse {
    success: boolean;
    run_url?: string;
    error?: string;
  }

  function triggerWorkflow(): void {
    const csrfToken = (
      document.querySelector("[name=csrfmiddlewaretoken]") as HTMLInputElement
    )?.value;
    const triggerUrl = document.body.dataset.workflowTriggerUrl;

    if (!csrfToken || !triggerUrl) {
      alert("Error: Missing required data");
      return;
    }

    fetch(triggerUrl, {
      method: "POST",
      headers: {
        "X-CSRFToken": csrfToken,
        "X-Requested-With": "XMLHttpRequest",
      },
    })
      .then((response) => response.json() as Promise<WorkflowResponse>)
      .then((data) => {
        if (data.success && data.run_url) {
          window.location.href = data.run_url;
        } else {
          alert("Error: " + (data.error || "Unknown error"));
        }
      })
      .catch((error) => {
        console.error("Error triggering workflow:", error);
        alert("Error triggering workflow: " + error);
      });
  }

  function toggleWorkflow(): void {
    const csrfToken = (
      document.querySelector("[name=csrfmiddlewaretoken]") as HTMLInputElement
    )?.value;
    const toggleUrl = document.body.dataset.workflowToggleUrl;

    if (!csrfToken || !toggleUrl) {
      alert("Error: Missing required data");
      return;
    }

    fetch(toggleUrl, {
      method: "POST",
      headers: {
        "X-CSRFToken": csrfToken,
        "X-Requested-With": "XMLHttpRequest",
      },
    })
      .then((response) => response.json() as Promise<WorkflowResponse>)
      .then((data) => {
        if (data.success) {
          window.location.reload();
        } else {
          alert("Error: " + (data.error || "Unknown error"));
        }
      })
      .catch((error) => {
        console.error("Error toggling workflow:", error);
        alert("Error toggling workflow: " + error);
      });
  }

  // Expose functions to global scope
  (window as any).triggerWorkflow = triggerWorkflow;
  (window as any).toggleWorkflow = toggleWorkflow;
})();
