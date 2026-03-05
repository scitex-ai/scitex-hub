// Workflow run detail page functionality

(function () {
  "use strict";

  function toggleJob(jobId: string | number): void {
    console.log("Toggling job:", jobId);
    const stepsDiv = document.getElementById(`job-${jobId}-steps`);
    const chevron = document.getElementById(`job-${jobId}-chevron`);

    if (!stepsDiv || !chevron) {
      console.error("Job elements not found:", jobId);
      return;
    }

    stepsDiv.classList.toggle("show");

    if (stepsDiv.classList.contains("show")) {
      chevron.classList.remove("bi-chevron-down");
      chevron.classList.add("bi-chevron-up");
    } else {
      chevron.classList.remove("bi-chevron-up");
      chevron.classList.add("bi-chevron-down");
    }
  }

  function toggleStep(stepId: string | number): void {
    console.log("Toggling step:", stepId);
    const outputDiv = document.getElementById(`step-${stepId}-output`);
    const chevron = document.getElementById(`step-${stepId}-chevron`);

    if (!outputDiv || !chevron) {
      console.error("Step elements not found:", stepId);
      return;
    }

    outputDiv.classList.toggle("show");

    if (outputDiv.classList.contains("show")) {
      chevron.classList.remove("bi-chevron-down");
      chevron.classList.add("bi-chevron-up");
    } else {
      chevron.classList.remove("bi-chevron-up");
      chevron.classList.add("bi-chevron-down");
    }
  }

  // Auto-refresh for in-progress runs
  document.addEventListener("DOMContentLoaded", function () {
    const container = document.querySelector(".container-fluid") as HTMLElement;
    if (container && container.dataset.runStatus === "in_progress") {
      console.log("Run in progress, auto-refresh enabled");
      setTimeout(function () {
        location.reload();
      }, 5000); // Refresh every 5 seconds
    }
  });

  // Expose functions to global scope
  (window as any).toggleJob = toggleJob;
  (window as any).toggleStep = toggleStep;
})();
