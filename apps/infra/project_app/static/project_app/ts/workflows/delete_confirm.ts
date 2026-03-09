/**
 * Workflow delete confirmation page functionality
 * Corresponds to: templates/project_app/workflows/delete_confirm.html
 */

class WorkflowDeleteConfirmPage {
  private form: HTMLFormElement | null;

  constructor() {
    this.form = document.querySelector("form.workflow-delete-form");
    this.init();
  }

  private init(): void {
    console.log("[WorkflowDeleteConfirm] Initializing delete confirmation");
    if (this.form) {
      this.setupConfirmation();
    }
  }

  private setupConfirmation(): void {
    // No confirmation needed — user explicitly submitted the form
  }
}

document.addEventListener("DOMContentLoaded", () => {
  new WorkflowDeleteConfirmPage();
});
