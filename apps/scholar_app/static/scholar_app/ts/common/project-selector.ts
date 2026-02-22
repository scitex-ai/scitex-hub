/**

 * Project Selector Handler for Scholar App
 * Manages project selection and persists the selection in sessionStorage
 */

console.log(
  "[DEBUG] apps/scholar_app/static/scholar_app/ts/common/project-selector.ts loaded",
);
function initProjectSelector(): void {
  const projectSelector = document.getElementById(
    "project-selector",
  ) as HTMLSelectElement | null;

  if (projectSelector) {
    // Store selected project in sessionStorage for use by save functions
    projectSelector.addEventListener(
      "change",
      function (this: HTMLSelectElement): void {
        if (this.value) {
          sessionStorage.setItem("scholar_selected_project_id", this.value);
          console.log("[Scholar] Selected project ID:", this.value);
        } else {
          sessionStorage.removeItem("scholar_selected_project_id");
          console.log("[Scholar] Cleared project selection");
        }
      },
    );

    // Initialize from sessionStorage on page load
    const savedProjectId: string | null = sessionStorage.getItem(
      "scholar_selected_project_id",
    );
    if (savedProjectId) {
      projectSelector.value = savedProjectId;
    }
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", function () {
    initProjectSelector();
  });
} else {
  initProjectSelector();
}
