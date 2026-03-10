/**
 * Scholar Workspace Initialization
 *
 * Handles the "Initialize Scholar" button click that POSTs to the
 * scholar initialize API endpoint.
 *
 * @module scholar-init
 */

function initScholarWorkspace(): void {
  const btn = document.getElementById(
    "init-scholar-btn",
  ) as HTMLButtonElement | null;
  if (!btn) return;

  const configEl = document.getElementById("scholar-init-config");
  const projectId = configEl ? configEl.getAttribute("data-project-id") : null;
  const csrfToken = configEl ? configEl.getAttribute("data-csrf-token") : null;

  btn.disabled = true;
  btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Initializing...';

  fetch("/apps/scholar/api/initialize/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken || "",
    },
    body: JSON.stringify({ project_id: projectId }),
  })
    .then(function (r) {
      return r.json();
    })
    .then(function (data) {
      if (data.success) {
        window.location.reload();
      } else {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-magic me-2"></i>Initialize Scholar';
        alert("Failed: " + (data.error || "Unknown error"));
      }
    })
    .catch(function (err: Error) {
      btn.disabled = false;
      btn.innerHTML = '<i class="fas fa-magic me-2"></i>Initialize Scholar';
      alert("Error: " + err.message);
    });
}

function init(): void {
  const btn = document.getElementById("init-scholar-btn");
  if (!btn) return;
  btn.addEventListener("click", initScholarWorkspace);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}

export { initScholarWorkspace };
