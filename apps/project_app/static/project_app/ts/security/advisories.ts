/**
 * Security advisories page functionality
 * Corresponds to: templates/project_app/security/advisories.html
 */

class SecurityAdvisoriesPage {
  constructor() {
    this.init();
  }

  private init(): void {
    console.log("[SecurityAdvisories] Initializing advisories page");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  new SecurityAdvisoriesPage();
});
