/**
 * ArXiv submission page functionality
 * Corresponds to: templates/writer_app/arxiv/submission.html
 */

class ArxivSubmissionPage {
  private form: HTMLFormElement | null;

  constructor() {
    this.form = document.querySelector("form#arxiv-submission-form");
    this.init();
  }

  private init(): void {
    console.log("[ArxivSubmission] Initializing arXiv submission page");
    this.setupFormValidation();
  }

  private setupFormValidation(): void {
    if (this.form) {
      this.form.addEventListener("submit", (e) => {
        e.preventDefault();
        this.submitToArxiv();
      });
    }
  }

  private async submitToArxiv(): Promise<void> {
    console.log("[ArxivSubmission] Submitting to arXiv");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  new ArxivSubmissionPage();
});
