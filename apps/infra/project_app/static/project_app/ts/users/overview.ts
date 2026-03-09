/**
 * User overview page functionality
 * Corresponds to: templates/project_app/users/overview.html
 */

class UserOverviewPage {
  constructor() {
    this.init();
  }

  private init(): void {
    console.log("[UserOverview] Initializing user overview");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  new UserOverviewPage();
});
