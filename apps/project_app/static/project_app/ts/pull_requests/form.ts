/**
 * Pull request form page functionality
 * Corresponds to: templates/project_app/pull_requests/form.html
 */

class PullRequestFormPage {
  private form: HTMLFormElement | null;

  constructor() {
    this.form = document.querySelector("form.pr-form");
    this.init();
  }

  private init(): void {
    console.log("[PRForm] Initializing pull request form");
    if (this.form) {
      this.setupFormHandling();
    }
  }

  private setupFormHandling(): void {
    this.form?.addEventListener("submit", (_e) => {
      console.log("[PRForm] Form submitted");
    });
  }
}

document.addEventListener("DOMContentLoaded", () => {
  new PullRequestFormPage();
});
