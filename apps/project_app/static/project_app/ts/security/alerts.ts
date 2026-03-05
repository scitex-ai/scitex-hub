/**
 * Security alerts page functionality
 * Corresponds to: templates/project_app/security/alerts.html
 */

class SecurityAlertsPage {
  constructor() {
    this.init();
  }

  private init(): void {
    console.log("[SecurityAlerts] Initializing alerts page");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  new SecurityAlertsPage();
});
